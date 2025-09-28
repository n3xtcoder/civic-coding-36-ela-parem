"""
Main Telegram bot application for educational video content delivery.
Refactored for better performance, cleaner code, and lean logging.
"""
import asyncio
import random
import time
from typing import Optional, Dict, Any

from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

from config import Config
from models import UserState, UserLevel, VideoInfo, AssessmentResult, VideoConversationContext
from airtable_service import get_user, create_user, update_user, create_message, get_videos, extract_video_info, invalidate_user_cache
from conversation_service import define_placement_group, assess_video_response
from logger import main_logger, performance_monitor
from cache import video_cache, user_cache
from utils import BotResponseHandler, VideoManager, KeyboardFactory, UserStateManager, ErrorHandler

# Initialize bot
bot = Bot(token=Config.BOT_TOKEN)
dp = Dispatcher()

# Load welcome message with caching
@performance_monitor("load_welcome_message")
def load_welcome_message() -> tuple[str, str, str]:
    """Load welcome message with caching."""
    cache_key = "welcome_message"
    cached_data = video_cache.get(cache_key)
    
    if cached_data:
        return cached_data
    
    welcome_message = get_videos(level=Config.USER_LEVELS["ENTRY"])
    if welcome_message:
        title = welcome_message[0]['fields']['Title']
        description = welcome_message[0]['fields']['Description']
        question = welcome_message[0]['fields']['Question']
    else:
        title = Config.MESSAGES["WELCOME_NOT_FOUND"]
        description = ""
        question = ""
    
    result = (title, description, question)
    video_cache.set(cache_key, result, ttl=3600)  # Cache for 1 hour
    return result

welcome_title, welcome_description, welcome_question = load_welcome_message()

# Global conversation context storage
# Key: user_id, Value: VideoConversationContext
user_conversations: Dict[int, VideoConversationContext] = {}

# Global review session storage
# Key: user_id, Value: Dict with original progress info
user_review_sessions: Dict[int, Dict[str, Any]] = {}

class ConversationManager:
    """Manages conversation context for users within videos."""
    
    @staticmethod
    def get_or_create_context(user_id: int, video_data: VideoInfo) -> VideoConversationContext:
        """Get existing conversation context or create new one for a video."""
        if user_id not in user_conversations:
            user_conversations[user_id] = VideoConversationContext(
                video_record_id=video_data.record_id,
                video_title=video_data.title,
                video_question=video_data.question,
                understanding_benchmark=video_data.understanding_benchmark,
                conversation_history=[],
                created_at=time.time()
            )
        return user_conversations[user_id]
    
    @staticmethod
    def update_context_for_video(user_id: int, video_data: VideoInfo) -> VideoConversationContext:
        """Update conversation context when user moves to a new video."""
        # Clear old conversation and create new context
        user_conversations[user_id] = VideoConversationContext(
            video_record_id=video_data.record_id,
            video_title=video_data.title,
            video_question=video_data.question,
            understanding_benchmark=video_data.understanding_benchmark,
            conversation_history=[],
            created_at=time.time()
        )
        return user_conversations[user_id]
    
    @staticmethod
    def add_user_message(user_id: int, content: str, message_id: Optional[str] = None) -> None:
        """Add a user message to the conversation context."""
        if user_id in user_conversations:
            user_conversations[user_id].add_message("user", content, message_id)
    
    @staticmethod
    def add_assistant_message(user_id: int, content: str, message_id: Optional[str] = None) -> None:
        """Add an assistant message to the conversation context."""
        if user_id in user_conversations:
            user_conversations[user_id].add_message("assistant", content, message_id)
    
    @staticmethod
    def get_conversation_context(user_id: int) -> Optional[VideoConversationContext]:
        """Get the current conversation context for a user."""
        return user_conversations.get(user_id)
    
    @staticmethod
    def clear_conversation(user_id: int) -> None:
        """Clear conversation context for a user."""
        if user_id in user_conversations:
            del user_conversations[user_id]
    
    @staticmethod
    def cleanup_user_data(user_id: int) -> None:
        """Clean up all user data from memory (conversations and review sessions)."""
        if user_id in user_conversations:
            del user_conversations[user_id]
            main_logger.log_system_event("user_conversation_cleaned", {
                "user_id": user_id,
                "reason": "user_deleted_from_airtable"
            })
        
        if user_id in user_review_sessions:
            del user_review_sessions[user_id]
            main_logger.log_system_event("user_review_session_cleaned", {
                "user_id": user_id,
                "reason": "user_deleted_from_airtable"
            })

# Utility Functions
@performance_monitor("assess_placement_test")
def assess_placement_test(question: str, answer: str) -> str:
    """Assess placement test using Mistral AI with fallback to random assignment."""
    try:
        result = define_placement_group(question, answer)
        main_logger.log_user_action(0, "placement_assessment", {
            "result": result,
            "method": "mistral"
        })
        return result
    except Exception as e:
        main_logger.log_error("placement_assessment_fallback", {
            "error": str(e)
        })
        # Fallback to random assignment if Mistral AI fails
        random_number = random.randint(1, 3)
        level_map = {1: "Beginner", 2: "Intermediate", 3: "Advanced"}
        result = level_map[random_number]
        main_logger.log_user_action(0, "placement_assessment", {
            "result": result,
            "method": "random_fallback"
        })
        return result

def get_next_level(current_level: str) -> str:
    """Get the next level in progression."""
    return Config.LEVEL_PROGRESSION.get(current_level, Config.USER_LEVELS["BEGINNER"])

def create_ready_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard with a 'Start' button for the placement test."""
    return KeyboardFactory.create_ready_keyboard()

def create_next_video_keyboard() -> ReplyKeyboardMarkup:
    """Create keyboard with 'Next Video' and 'Overview' buttons for chat mode."""
    return KeyboardFactory.create_next_video_keyboard()

def get_video_info(user_level: str, video_number: int) -> Optional[VideoInfo]:
    """Get video information for a specific level and video number with caching."""
    return VideoManager.get_video_info_cached(user_level, video_number)

def get_user_record_id(user: Dict[str, Any], user_id: int) -> Optional[str]:
    """Get user record ID with proper error handling."""
    if not user:
        main_logger.log_error("user_data_not_found", {
            "user_id": user_id
        })
        return None
        
    user_record_id = user.get('id')
    if not user_record_id:
        main_logger.log_error("user_no_record_id", {
            "user_id": user_id
        })
        return None
        
    return user_record_id

@performance_monitor("generate_course_overview")
def generate_course_overview_text(user_level: str, current_video_number: int) -> str:
    """
    Generate course overview text without interactive elements.
    Optimized with caching and lean logging.
    """
    try:
        # Check cache first
        cache_key = f"course_overview:{user_level}:{current_video_number}"
        cached_data = video_cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # Get all videos from all levels
        all_videos = get_videos()  # No level filter to get all videos
        
        if not all_videos:
            return f"📋 **Kursübersicht**\n\nKeine Videos gefunden."
        
        # Group videos by level efficiently
        videos_by_level = {}
        for video_record in all_videos:
            level = video_record['fields'].get('Level', 'Unknown')
            if level not in videos_by_level:
                videos_by_level[level] = []
            videos_by_level[level].append(video_record)
        
        # Sort levels in progression order
        level_order = ["Entry", "Beginner", "Intermediate", "Advanced"]
        sorted_levels = [level for level in level_order if level in videos_by_level]
        
        # Add any levels not in the standard order
        for level in videos_by_level:
            if level not in sorted_levels:
                sorted_levels.append(level)
        
        overview_lines = ["📋 **Kursübersicht**\n"]
        
        total_completed_videos = 0
        total_videos = len(all_videos)
        current_level_reached = False
        
        for level in sorted_levels:
            level_videos = videos_by_level[level]
            # Sort videos by video number within each level
            sorted_level_videos = sorted(level_videos, key=lambda x: x['fields'].get('Video Number', x['fields'].get('# Video Number', 0)))
            
            # Determine if this is the current level
            is_current_level = level == user_level
            
            # Add level header
            if is_current_level:
                overview_lines.append(f"📍 **{level} Level** (Aktuell)")
            else:
                overview_lines.append(f"📚 **{level} Level**")
            
            for video_record in sorted_level_videos:
                video_info = extract_video_info(video_record)
                video_num = video_info.video_number
                
                # Determine status indicator
                if is_current_level:
                    if video_num < current_video_number:
                        status = "✅"  # Completed
                        video_text = f"📹 {video_info.title}"
                        total_completed_videos += 1
                    elif video_num == current_video_number:
                        status = "📍"  # Current
                        video_text = f"📹 {video_info.title}"
                    else:
                        status = "⏳"  # Upcoming
                        video_text = f"📹 {video_info.title}"
                elif not current_level_reached:
                    # Previous levels - all completed
                    status = "✅"
                    video_text = f"📹 {video_info.title}"
                    total_completed_videos += 1
                else:
                    # Future levels - all upcoming
                    status = "⏳"
                    video_text = f"📹 {video_info.title}"
                
                overview_lines.append(f"  {status} Video {video_num}: {video_text}")
            
            # Mark that we've reached the current level
            if is_current_level:
                current_level_reached = True
            
            overview_lines.append("")  # Empty line between levels
        
        # Add progress indicator
        progress_percentage = (total_completed_videos / total_videos * 100) if total_videos > 0 else 0
        overview_lines.append(f"📊 **Gesamtfortschritt**: {total_completed_videos}/{total_videos} Videos ({progress_percentage:.0f}%)")
        
        result = "\n".join(overview_lines)
        
        # Cache the result
        video_cache.set(cache_key, result, ttl=300)  # Cache for 5 minutes
        
        main_logger.log_system_event("course_overview_generated", {
            "user_level": user_level,
            "current_video": current_video_number,
            "total_videos": total_videos,
            "completed_videos": total_completed_videos
        })
        
        return result
        
    except Exception as e:
        main_logger.log_error("course_overview_error", {
            "user_level": user_level,
            "current_video": current_video_number,
            "error": str(e)
        })
        return f"📋 **Kursübersicht**\n\nFehler beim Laden der Übersicht."

def create_course_overview_keyboard(user_level: str, current_video_number: int) -> InlineKeyboardMarkup:
    """Create inline keyboard with clickable video titles for course overview."""
    return KeyboardFactory.create_course_overview_keyboard(user_level, current_video_number)

def log_user_message(message_text: str, video_record_id: Optional[str] = None) -> None:
    """Log user message to Airtable."""
    create_message(message_text, "User", video_record_id)

def log_bot_message(message_text: str, video_record_id: Optional[str] = None) -> None:
    """Log bot message to Airtable."""
    create_message(message_text, "Bot", video_record_id)

def cleanup_user_data_from_memory(user_id: int) -> None:
    """Clean up all user data from memory when user is deleted from Airtable."""
    ConversationManager.cleanup_user_data(user_id)
    # Also invalidate user cache to ensure fresh data on next access
    invalidate_user_cache(user_id)


@performance_monitor("safe_update_user")
async def safe_update_user(user: Dict[str, Any], delay_seconds: float = 0.5) -> bool:
    """
    Safely update user data with a small delay to avoid interfering with message creation.
    Optimized with better error handling and lean logging.
    
    Args:
        user: The user record to update
        delay_seconds: Delay before updating to ensure message operations complete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Small delay to ensure any pending message operations complete
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
        
        result = update_user(user_data=user)
        
        if result:
            main_logger.log_system_event("user_update_success", {
                "user_id": user.get('id'),
                "telegram_id": user['fields'].get('Telegram ID')
            })
        else:
            main_logger.log_error("user_update_failed", {
                "user_id": user.get('id'),
                "telegram_id": user['fields'].get('Telegram ID')
            })
        
        return result
    except Exception as e:
        main_logger.log_error("user_update_error", {
            "user_id": user.get('id', 'unknown'),
            "error": str(e)
        })
        return False

# State Handler Functions
@performance_monitor("handle_placement_test")
async def handle_placement_test_state(message: Message, user: Dict[str, Any]) -> None:
    """Handle messages when user is in Placement Test state."""
    user_id = message.from_user.id
    user_record_id = get_user_record_id(user, user_id)
    
    if not user_record_id:
        await message.answer("Fehler beim Abrufen der Benutzerdaten. Bitte versuche es erneut.")
        return
    
    # Log user message to Airtable (no video associated with placement test)
    log_user_message(message.text)
    
    # Assess the placement test answer
    placement_group = assess_placement_test(welcome_question, message.text)
    
    # Update user data
    user['fields']['Level'] = placement_group
    user['fields']['State'] = UserState.SHOWING_VIDEO.value
    user['fields']['Video Number'] = 1
    
    # Send response with ready button first
    bot_response = "Perfekt! Du bist bereit für dein erstes Video."
    log_bot_message(bot_response)  # No video associated yet
    await message.answer(bot_response, reply_markup=create_ready_keyboard())
    
    # Update user data after message operations complete
    await safe_update_user(user)
    
    main_logger.log_user_action(user_id, "placement_test_completed", {
        "placement_group": placement_group
    })

@performance_monitor("handle_showing_video")
async def handle_showing_video_state(message: Message, user: Dict[str, Any]) -> None:
    """Handle messages when user is in Showing Video state."""
    user_id = message.from_user.id
    user_level, video_number = UserStateManager.get_user_progress(user)
    
    # Get video information
    video_info = get_video_info(user_level, video_number)
    
    if video_info:
        # Send video information
        if video_info.url:
            await BotResponseHandler.send_response(message, f"📹 {video_info.title}. \n {video_info.description}")
            await asyncio.sleep(2)
            await BotResponseHandler.send_response(message, f"🎥 Video: {video_info.url}")
        else:
            await BotResponseHandler.send_response(message, f"📹 {video_info.title}")
        
        # Wait and ask question
        await asyncio.sleep(Config.VIDEO_WAIT_TIME)
        await BotResponseHandler.send_response(message, f"❓ {video_info.question}")
        
        # Update state to Waiting for Response
        UserStateManager.transition_user_state(user, UserState.WAITING_FOR_RESPONSE)
        await safe_update_user(user)
        
        main_logger.log_user_action(user_id, "video_shown", {
            "video_title": video_info.title,
            "level": user_level,
            "video_number": video_number
        })
    else:
        await ErrorHandler.handle_video_not_found(message, user_id)

@performance_monitor("handle_waiting_for_response")
async def handle_waiting_for_response_state(message: Message, user: Dict[str, Any]) -> None:
    """Handle messages when user is in Waiting for Response state."""
    user_id = message.from_user.id
    user_record_id = get_user_record_id(user, user_id)
    
    if not user_record_id:
        await ErrorHandler.handle_user_data_error(message, user_id)
        return
        
    user_level, video_number = UserStateManager.get_user_progress(user)
    
    # Get video information for assessment
    video_data = get_video_info(user_level, video_number)
    
    if video_data:
        # Create or get conversation context for this video
        conversation_context = ConversationManager.get_or_create_context(user_id, video_data)
        
        # Log user message with video reference
        message_record = create_message(message.text, "User", video_data.record_id)
        message_id = message_record['id'] if message_record else None
        
        # Add user message to conversation context
        ConversationManager.add_user_message(user_id, message.text, message_id)
        
        # Get conversation history for context
        conversation_history = conversation_context.get_conversation_summary()
        
        # Assess the response using Mistral AI with conversation context
        try:
            assessment = assess_video_response(
                video_data.question, 
                message.text, 
                video_data.understanding_benchmark,
                conversation_history
            )
            bot_response = f"💭 {assessment.feedback}"
        except Exception as e:
            main_logger.log_error("assessment_failed", {
                "user_id": user_id,
                "error": str(e)
            })
            bot_response = f"Danke für deine Antwort: {message.text}"
        
        # Log and send response
        bot_message_record = create_message(bot_response, "Bot", video_data.record_id)
        bot_message_id = bot_message_record['id'] if bot_message_record else None
        
        # Add assistant message to conversation context
        ConversationManager.add_assistant_message(user_id, bot_response, bot_message_id)
        
        await BotResponseHandler.send_response(message, bot_response, create_next_video_keyboard(), user_id)
        
        main_logger.log_user_action(user_id, "video_response_assessed", {
            "video_title": video_data.title,
            "response_length": len(message.text)
        })
    else:
        # Fallback if video not found
        log_user_message(message.text)
        bot_response = f"Danke für deine Antwort: {message.text}"
        log_bot_message(bot_response)
        await BotResponseHandler.send_response(message, bot_response, create_next_video_keyboard(), user_id)
    
    # Update state to Chat Mode
    UserStateManager.transition_user_state(user, UserState.CHAT_MODE)
    await safe_update_user(user)

@performance_monitor("handle_chat_mode")
async def handle_chat_mode_state(message: Message, user: Dict[str, Any]) -> None:
    """Handle messages when user is in Chat Mode state."""
    user_id = message.from_user.id
    user_record_id = get_user_record_id(user, user_id)
    
    if not user_record_id:
        await ErrorHandler.handle_user_data_error(message, user_id)
        return
        
    user_level, video_number = UserStateManager.get_user_progress(user)
    
    # Get video information for assessment
    video_data = get_video_info(user_level, video_number)
    
    if video_data:
        # Get existing conversation context for this video
        conversation_context = ConversationManager.get_conversation_context(user_id)
        
        # Log user message with video reference
        message_record = create_message(message.text, "User", video_data.record_id)
        message_id = message_record['id'] if message_record else None
        
        # Add user message to conversation context
        ConversationManager.add_user_message(user_id, message.text, message_id)
        
        # Get conversation history for context
        conversation_history = conversation_context.get_conversation_summary() if conversation_context else ""
        
        # Assess the response using Mistral AI with conversation context
        try:
            assessment = assess_video_response(
                video_data.question, 
                message.text, 
                video_data.understanding_benchmark,
                conversation_history
            )
            bot_response = f"💭 {assessment.feedback}"
        except Exception as e:
            main_logger.log_error("chat_assessment_failed", {
                "user_id": user_id,
                "error": str(e)
            })
            bot_response = f"Du hast gesagt: {message.text}"
        
        # Log and send response
        bot_message_record = create_message(bot_response, "Bot", video_data.record_id)
        bot_message_id = bot_message_record['id'] if bot_message_record else None
        
        # Add assistant message to conversation context
        ConversationManager.add_assistant_message(user_id, bot_response, bot_message_id)
        
        await BotResponseHandler.send_response(message, bot_response, create_next_video_keyboard(), user_id)
        
        main_logger.log_user_action(user_id, "chat_message_processed", {
            "video_title": video_data.title,
            "message_length": len(message.text)
        })
    else:
        # Fallback if video not found
        log_user_message(message.text)
        bot_response = f"Du hast gesagt: {message.text}"
        log_bot_message(bot_response)
        await BotResponseHandler.send_response(message, bot_response, create_next_video_keyboard(), user_id)

@performance_monitor("handle_course_overview")
async def handle_course_overview_state(message: Message, user: Dict[str, Any]) -> None:
    """Handle messages when user is in Course Overview state."""
    user_id = message.from_user.id
    user_record_id = get_user_record_id(user, user_id)
    
    if not user_record_id:
        await ErrorHandler.handle_user_data_error(message, user_id)
        return
    
    # Log user message (no video context for general course questions)
    log_user_message(message.text)
    
    # For now, provide a simple response for general course questions
    # This could be enhanced with Mistral AI to answer general course questions
    bot_response = f"Das ist eine gute Frage zum Kurs! Du kannst spezifische Videos auswählen, indem du auf die Video-Titel in der Übersicht klickst. Oder du kannst mit 'Verstanden!' zum nächsten Video in deinem aktuellen Level fortfahren."
    
    log_bot_message(bot_response)
    
    # Send response without any keyboard (buttons disappear as requested)
    await BotResponseHandler.send_response(message, bot_response, user_id=user_id)
    
    main_logger.log_user_action(user_id, "course_overview_interaction", {
        "message_length": len(message.text)
    })

# Callback Handler Functions
async def handle_next_video_callback(callback_query: types.CallbackQuery, user: Dict[str, Any]) -> None:
    """Handle Next Video button click."""
    user_id = callback_query.from_user.id
    user_level = user['fields'].get('Level', '')
    current_video_number = user['fields'].get('Video Number', 1)
    
    # Increment video number
    new_video_number = current_video_number + 1
    
    # Check if we need to progress to next level
    if new_video_number > Config.MAX_VIDEOS_PER_LEVEL:
        new_level = get_next_level(user_level)
        new_video_number = 1
        user['fields']['Level'] = new_level
        await callback_query.message.answer(Config.MESSAGES["CONGRATULATIONS"].format(level=new_level))
    else:
        user['fields']['Level'] = user_level
    
    # Update user data
    user['fields']['Video Number'] = new_video_number
    user['fields']['State'] = UserState.SHOWING_VIDEO.value
    await safe_update_user(user)
    
    # Clear conversation context for the new video
    user_level = user['fields'].get('Level', '')
    video_data = get_video_info(user_level, new_video_number)
    if video_data:
        ConversationManager.update_context_for_video(user_id, video_data)
    
    # Acknowledge callback
    await callback_query.answer(Config.MESSAGES["NEXT_VIDEO_LOADING"])
    
    # Start showing the next video
    await handle_showing_video_state(callback_query.message, user)

async def handle_ready_callback(callback_query: types.CallbackQuery, user: Dict[str, Any]) -> None:
    """Handle Ready button click after placement test."""
    user_id = callback_query.from_user.id
    
    # Acknowledge callback
    await callback_query.answer(Config.MESSAGES["VIDEO_LOADING"])
    
    # Start showing the first video
    await handle_showing_video_state(callback_query.message, user)

async def handle_video_selection_callback(callback_query: types.CallbackQuery, user: Dict[str, Any], video_record_id: str, is_review: bool = False) -> None:
    """Handle video selection from course overview."""
    user_id = callback_query.from_user.id
    user_record_id = get_user_record_id(user, user_id)
    
    if not user_record_id:
        await callback_query.answer("Fehler beim Abrufen der Benutzerdaten.")
        return
    
    try:
        # Get video information from Airtable
        videos = get_videos()
        selected_video = None
        
        for video_record in videos:
            if video_record.get('id') == video_record_id:
                selected_video = video_record
                break
        
        if not selected_video:
            await callback_query.answer("Video nicht gefunden.")
            return
        
        video_info = extract_video_info(selected_video)
        
        # Store original progress before potentially changing it
        original_level = user['fields'].get('Level', '')
        original_video_number = user['fields'].get('Video Number', 1)
        
        # Update user data to the selected video (temporarily for viewing)
        user['fields']['Level'] = video_info.level
        user['fields']['Video Number'] = video_info.video_number
        user['fields']['State'] = UserState.SHOWING_VIDEO.value
        
        # Only update progress in Airtable if it's not a review
        if not is_review:
            await safe_update_user(user)
        else:
            # For reviews, store original progress to restore later
            user_review_sessions[user_id] = {
                'original_level': original_level,
                'original_video_number': original_video_number,
                'review_video_id': video_record_id
            }
            main_logger.log_system_event("user_review_session_started", {
                "user_id": user_id,
                "video_title": video_info.title,
                "original_level": original_level,
                "original_video_number": original_video_number
            })
        
        # Clear conversation context for the new video
        ConversationManager.update_context_for_video(user_id, video_info)
        
        # Acknowledge callback
        review_text = " (Wiederholung)" if is_review else ""
        await callback_query.answer(f"Video wird geladen: {video_info.title}{review_text}")
        
        # Start showing the selected video
        await handle_showing_video_state(callback_query.message, user)
        
    except Exception as e:
        main_logger.log_error(f"Error handling video selection: {e}")
        await callback_query.answer("Fehler beim Laden des Videos.")

async def handle_next_video_from_reply(message: Message, user: Dict[str, Any]) -> None:
    """Handle Next Video button press from reply keyboard."""
    user_id = message.from_user.id
    user_level = user['fields'].get('Level', '')
    current_video_number = user['fields'].get('Video Number', 1)
    
    # Increment video number
    new_video_number = current_video_number + 1
    
    # Check if we need to progress to next level
    if new_video_number > Config.MAX_VIDEOS_PER_LEVEL:
        new_level = get_next_level(user_level)
        new_video_number = 1
        user['fields']['Level'] = new_level
        await message.answer(Config.MESSAGES["CONGRATULATIONS"].format(level=new_level))
    else:
        user['fields']['Level'] = user_level
    
    # Update user data
    user['fields']['Video Number'] = new_video_number
    user['fields']['State'] = UserState.SHOWING_VIDEO.value
    await safe_update_user(user)
    
    # Clear conversation context for the new video
    user_level = user['fields'].get('Level', '')
    video_data = get_video_info(user_level, new_video_number)
    if video_data:
        ConversationManager.update_context_for_video(user_id, video_data)
    
    # Start showing the next video
    await handle_showing_video_state(message, user)

async def handle_overview_button(message: Message, user: Dict[str, Any]) -> None:
    """Handle Overview button press from reply keyboard."""
    user_id = message.from_user.id
    user_record_id = get_user_record_id(user, user_id)
    
    if not user_record_id:
        await message.answer("Fehler beim Abrufen der Benutzerdaten. Bitte versuche es erneut.")
        return
    
    user_level = user['fields'].get('Level', '')
    current_video_number = user['fields'].get('Video Number', 1)
    
    # Generate course overview text and keyboard
    overview_text = generate_course_overview_text(user_level, current_video_number)
    overview_keyboard = create_course_overview_keyboard(user_level, current_video_number)
    
    # Log the overview request
    log_user_message(message.text)
    log_bot_message(overview_text)
    
    # Update user state to course overview mode
    user['fields']['State'] = UserState.COURSE_OVERVIEW.value
    await safe_update_user(user)
    
    # Send overview with interactive keyboard
    await message.answer(overview_text, parse_mode='Markdown', reply_markup=overview_keyboard)

# Bot Command Handlers
@dp.message(Command("start"))
async def start(message: Message) -> None:
    """Handle /start command."""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user:
        user_record_id = user['id']  # Get Airtable record ID
        if not user_record_id:
            main_logger.log_error(f"User {user_id} exists but has no Airtable record ID")
            await message.answer("Fehler beim Abrufen der Benutzerdaten. Bitte versuche es erneut.")
            return
            
        bot_response = Config.MESSAGES["ALREADY_REGISTERED"]
        log_bot_message(bot_response)  # No video associated with start command
        await message.answer(bot_response)
        return
    
    # User not found in Airtable - clean up any existing memory data
    cleanup_user_data_from_memory(user_id)
    
    # Create new user
    new_user = create_user(
        user_id=user_id,
        user_level=Config.USER_LEVELS["ENTRY"],
        user_video_number=0,
        user_state=UserState.PLACEMENT_TEST.value
    )
    
    if new_user and new_user.get('id'):
        user_record_id = new_user['id']  # Get Airtable record ID
        
        # Log welcome messages to Airtable (no video associated with welcome)
        log_bot_message(welcome_title)
        log_bot_message(welcome_description)
        log_bot_message(welcome_question)
        
        # Send welcome messages
        await message.answer(welcome_title)
        await asyncio.sleep(1)
        await message.answer(welcome_description)
        await asyncio.sleep(2)
        await message.answer(welcome_question)
    else:
        main_logger.log_error(f"Failed to create user {user_id} or user has no Airtable record ID")
        await message.answer("Fehler beim Erstellen des Benutzers. Bitte versuche es erneut.")

@dp.callback_query()
async def handle_callback(callback_query: types.CallbackQuery) -> None:
    """Handle callback queries from inline keyboards."""
    user_id = callback_query.from_user.id
    user = get_user(user_id)
    
    if not user:
        await callback_query.answer(Config.MESSAGES["USER_NOT_FOUND"])
        return
    
    callback_data = callback_query.data
    
    if callback_data == "ready_for_video":
        await handle_ready_callback(callback_query, user)
    elif callback_data == "next_video":
        await handle_next_video_callback(callback_query, user)
    elif callback_data.startswith("select_video:"):
        # Extract video record ID and review flag from callback data
        parts = callback_data.split(":", 2)
        video_record_id = parts[1]
        is_review = parts[2].lower() == "true" if len(parts) > 2 else False
        await handle_video_selection_callback(callback_query, user, video_record_id, is_review)

@dp.message()
async def handle_message(message: Message) -> None:
    """Main message handler that routes messages based on user state."""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        await message.answer(Config.MESSAGES["START_BOT_FIRST"])
        return
    
    user_state = user['fields'].get('State', '')
    
    # Check if user pressed "Verstanden!" button
    if message.text == Config.MESSAGES["UNDERSTOOD_BUTTON"] and user_state in [UserState.WAITING_FOR_RESPONSE.value, UserState.CHAT_MODE.value]:
        # Get current video information for logging
        user_record_id = get_user_record_id(user, user_id)
        
        if not user_record_id:
            await message.answer("Fehler beim Abrufen der Benutzerdaten. Bitte versuche es erneut.")
            return
            
        user_level = user['fields'].get('Level', '')
        video_number = user['fields'].get('Video Number', 1)
        video_data = get_video_info(user_level, video_number)
        
        # Check if user is finishing a review session
        if user_id in user_review_sessions:
            # Restore original progress
            review_session = user_review_sessions[user_id]
            original_level = review_session['original_level']
            original_video_number = review_session['original_video_number']
            
            # Restore user progress
            user['fields']['Level'] = original_level
            user['fields']['Video Number'] = original_video_number
            
            # Update Airtable with restored progress
            await safe_update_user(user)
            
            # Clear review session
            del user_review_sessions[user_id]
            
            # Log user message
            log_user_message(message.text, video_data.record_id if video_data else None)
            
            bot_response = f"Wiederholung beendet! Du bist zurück bei {original_level} Video {original_video_number}."
            log_bot_message(bot_response, video_data.record_id if video_data else None)
            
            await message.answer(bot_response, reply_markup=create_next_video_keyboard())
            return
        
        # Normal flow for non-review sessions
        # Log user message
        log_user_message(message.text, video_data.record_id if video_data else None)
        
        bot_response = Config.MESSAGES["NEXT_VIDEO_START"]
        log_bot_message(bot_response, video_data.record_id if video_data else None)
        
        await message.answer(bot_response)
        await asyncio.sleep(1)
        await handle_next_video_from_reply(message, user)
        return
    
    # Check if user pressed "Kursübersicht" button
    if message.text == Config.MESSAGES["OVERVIEW_BUTTON"] and user_state in [UserState.WAITING_FOR_RESPONSE.value, UserState.CHAT_MODE.value]:
        await handle_overview_button(message, user)
        return
    
    # Route messages based on user state
    if user_state == UserState.PLACEMENT_TEST.value:
        await handle_placement_test_state(message, user)
    elif user_state == UserState.SHOWING_VIDEO.value:
        await message.answer(Config.MESSAGES["VIDEO_PROCESSING"])
    elif user_state == UserState.WAITING_FOR_RESPONSE.value:
        await handle_waiting_for_response_state(message, user)
    elif user_state == UserState.CHAT_MODE.value:
        await handle_chat_mode_state(message, user)
    elif user_state == UserState.COURSE_OVERVIEW.value:
        await handle_course_overview_state(message, user)
    else:
        # Default fallback
        await message.answer(message.text)

async def main():
    """Main function to start the bot."""
    # Validate configuration before starting
    if not Config.validate_config():
        main_logger.log_error("configuration_validation_failed")
        exit(1)
    
    main_logger.log_system_event("bot_starting")
    
    # Start the bot
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())