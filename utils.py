"""
Common utilities and helper functions for the Telegram bot.
Extracted to reduce code duplication and improve maintainability.
"""
from typing import Dict, Any, Optional, List
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from models import UserState, VideoInfo
from config import Config
from logger import main_logger
from airtable_service import get_videos, extract_video_info
from cache import video_cache

class BotResponseHandler:
    """Handles bot responses with consistent logging and error handling."""
    
    @staticmethod
    async def send_response(message: Message, text: str, reply_markup=None, user_id: Optional[int] = None) -> None:
        """Send response with consistent error handling and logging."""
        try:
            await message.answer(text, reply_markup=reply_markup)
            if user_id:
                main_logger.log_user_action(user_id, "bot_response_sent", {
                    "response_length": len(text),
                    "has_markup": reply_markup is not None
                })
        except Exception as e:
            main_logger.log_error("response_send_error", {
                "user_id": user_id,
                "error": str(e),
                "text_length": len(text)
            })
            # Fallback response
            await message.answer("Entschuldigung, es gab einen Fehler. Bitte versuche es erneut.")

class VideoManager:
    """Manages video-related operations with caching."""
    
    @staticmethod
    def get_video_info_cached(user_level: str, video_number: int) -> Optional[VideoInfo]:
        """Get video information with caching."""
        cache_key = f"video_info:{user_level}:{video_number}"
        cached_data = video_cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        videos = get_videos(level=user_level, video_number=video_number)
        if videos:
            video_info = extract_video_info(videos[0])
            video_cache.set(cache_key, video_info, ttl=600)  # Cache for 10 minutes
            return video_info
        return None
    
    @staticmethod
    def invalidate_video_cache(user_level: str, video_number: int) -> None:
        """Invalidate video cache when video data changes."""
        cache_key = f"video_info:{user_level}:{video_number}"
        video_cache.delete(cache_key)

class KeyboardFactory:
    """Factory for creating consistent keyboards."""
    
    @staticmethod
    def create_ready_keyboard() -> InlineKeyboardMarkup:
        """Create keyboard with a 'Start' button for the placement test."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=Config.MESSAGES["READY_BUTTON"], callback_data="ready_for_video")]
        ])
    
    @staticmethod
    def create_next_video_keyboard() -> ReplyKeyboardMarkup:
        """Create keyboard with 'Next Video' and 'Overview' buttons for chat mode."""
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=Config.MESSAGES["UNDERSTOOD_BUTTON"]), 
                 KeyboardButton(text=Config.MESSAGES["OVERVIEW_BUTTON"])]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    
    @staticmethod
    def create_course_overview_keyboard(user_level: str, current_video_number: int) -> InlineKeyboardMarkup:
        """Create inline keyboard with clickable video titles for course overview."""
        try:
            # Get all videos from all levels
            all_videos = get_videos()
            
            if not all_videos:
                return InlineKeyboardMarkup(inline_keyboard=[])
            
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
            
            keyboard_buttons = []
            current_level_reached = False
            
            for level in sorted_levels:
                level_videos = videos_by_level[level]
                # Sort videos by video number within each level
                sorted_level_videos = sorted(level_videos, key=lambda x: x['fields'].get('Video Number', x['fields'].get('# Video Number', 0)))
                
                # Determine if this is the current level
                is_current_level = level == user_level
                
                for video_record in sorted_level_videos:
                    video_info = extract_video_info(video_record)
                    video_num = video_info.video_number
                    
                    # Determine if this video should be clickable
                    should_show_button = False
                    status = ""
                    
                    if is_current_level:
                        # Current level: show buttons for videos up to and including current
                        if video_num <= current_video_number:
                            should_show_button = True
                            if video_num < current_video_number:
                                status = "✅"
                            elif video_num == current_video_number:
                                status = "📍"
                    elif not current_level_reached:
                        # Previous levels: all videos are clickable
                        should_show_button = True
                        status = "✅"
                    else:
                        # Future levels: no buttons
                        should_show_button = False
                        status = "⏳"
                    
                    # Only create button if video should be clickable
                    if should_show_button:
                        # Create button text
                        button_text = f"{status} {level} Video {video_num}: {video_info.title[:30]}{'...' if len(video_info.title) > 30 else ''}"
                        
                        # Create callback data with video record ID and whether it's a review (previous video)
                        is_review = (is_current_level and video_num < current_video_number) or (not current_level_reached)
                        callback_data = f"select_video:{video_info.record_id}:{is_review}"
                        
                        keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
                
                # Mark that we've reached the current level
                if is_current_level:
                    current_level_reached = True
            
            return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
        except Exception as e:
            main_logger.log_error("keyboard_creation_error", {
                "user_level": user_level,
                "current_video": current_video_number,
                "error": str(e)
            })
            return InlineKeyboardMarkup(inline_keyboard=[])

class UserStateManager:
    """Manages user state transitions and validations."""
    
    @staticmethod
    def validate_user_state(user: Dict[str, Any], expected_states: List[str]) -> bool:
        """Validate that user is in one of the expected states."""
        user_state = user['fields'].get('State', '')
        return user_state in expected_states
    
    @staticmethod
    def transition_user_state(user: Dict[str, Any], new_state: UserState) -> None:
        """Transition user to new state with logging."""
        old_state = user['fields'].get('State', '')
        user['fields']['State'] = new_state.value
        
        main_logger.log_user_action(
            user['fields'].get('Telegram ID', 0),
            "state_transition",
            {
                "from_state": old_state,
                "to_state": new_state.value
            }
        )
    
    @staticmethod
    def get_user_progress(user: Dict[str, Any]) -> tuple[str, int]:
        """Get user's current level and video number."""
        level = user['fields'].get('Level', '')
        video_number = user['fields'].get('Video Number', 1)
        return level, video_number

class ErrorHandler:
    """Centralized error handling for consistent error responses."""
    
    @staticmethod
    async def handle_user_data_error(message: Message, user_id: int) -> None:
        """Handle user data retrieval errors."""
        main_logger.log_error("user_data_error", {"user_id": user_id})
        await message.answer("Fehler beim Abrufen der Benutzerdaten. Bitte versuche es erneut.")
    
    @staticmethod
    async def handle_video_not_found(message: Message, user_id: int) -> None:
        """Handle video not found errors."""
        main_logger.log_error("video_not_found", {"user_id": user_id})
        await message.answer(Config.MESSAGES["VIDEO_NOT_FOUND"])
    
    @staticmethod
    async def handle_general_error(message: Message, user_id: int, error: str) -> None:
        """Handle general errors."""
        main_logger.log_error("general_error", {
            "user_id": user_id,
            "error": error
        })
        await message.answer("Entschuldigung, es gab einen Fehler. Bitte versuche es erneut.")
