"""
Airtable service for managing data operations with caching and lean logging.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pyairtable import Api
from config import Config
from models import VideoRecord, UserRecord, MessageRecord, VideoInfo, UserData, MessageData
from logger import airtable_logger
from cache import video_cache, user_cache, cached

# Initialize Airtable API
api = Api(Config.AIRTABLE_API_KEY)
users_table = api.table(Config.AIRTABLE_BASE_ID, Config.USERS_TABLE_ID)
videos_table = api.table(Config.AIRTABLE_BASE_ID, Config.VIDEOS_TABLE_ID)
messages_table = api.table(Config.AIRTABLE_BASE_ID, Config.MESSAGES_TABLE_ID)

@cached(ttl=600)  # Cache for 10 minutes
def get_videos(level: Optional[str] = None, video_number: Optional[int] = None) -> List[VideoRecord]:
    """
    Retrieve videos from Airtable based on level and video number.
    
    Args:
        level: The difficulty level to filter by
        video_number: The specific video number to filter by
        
    Returns:
        List of video records matching the criteria
    """
    try:
        if level and video_number is not None:
            # Try different field name variations for Video Number
            field_variations = ["Video Number", "# Video Number"]
            
            for field_name in field_variations:
                try:
                    formula = f"AND({{Level}}='{level}', {{{field_name}}}={video_number})"
                    videos = videos_table.all(formula=formula)
                    if videos:
                        airtable_logger.log_system_event("video_query_success", {
                            "level": level, 
                            "video_number": video_number,
                            "field_name": field_name,
                            "count": len(videos)
                        })
                        return videos
                except Exception as e:
                    airtable_logger.log_error(f"video_query_field_error", {
                        "field_name": field_name,
                        "error": str(e)
                    })
                    continue
            
            # Fallback: get all videos for the level and filter manually
            airtable_logger.log_system_event("video_query_fallback", {
                "level": level,
                "video_number": video_number
            })
            all_videos = videos_table.all(formula=f"{{Level}}='{level}'")
            filtered_videos = [v for v in all_videos if v['fields'].get('Video Number') == video_number or v['fields'].get('# Video Number') == video_number]
            return filtered_videos
            
        elif level:
            videos = videos_table.all(formula=f"{{Level}}='{level}'")
            airtable_logger.log_system_event("video_query_by_level", {
                "level": level,
                "count": len(videos)
            })
            return videos
        else:
            videos = videos_table.all()
            airtable_logger.log_system_event("video_query_all", {
                "count": len(videos)
            })
            return videos
            
    except Exception as e:
        airtable_logger.log_error("video_query_error", {
            "level": level,
            "video_number": video_number,
            "error": str(e)
        })
        return []

@cached(ttl=300)  # Cache for 5 minutes
def get_user(user_id: int) -> Optional[UserRecord]:
    """
    Retrieve a user from Airtable by Telegram ID.
    
    Args:
        user_id: The Telegram user ID
        
    Returns:
        User record if found, None otherwise
    """
    try:
        users = users_table.all(formula=f"{{Telegram ID}}={user_id}")
        
        if users:
            user_record = users[0]
            airtable_logger.log_system_event("user_found", {
                "user_id": user_id,
                "airtable_id": user_record.get('id')
            })
            return user_record
        else:
            airtable_logger.log_system_event("user_not_found", {
                "user_id": user_id
            })
            return None
            
    except Exception as e:
        airtable_logger.log_error("user_query_error", {
            "user_id": user_id,
            "error": str(e)
        })
        return None

def create_user(user_id: int, user_level: str = "Entry", user_video_number: Optional[int] = None, user_state: str = "") -> Optional[UserRecord]:
    """
    Create a new user in Airtable if they don't already exist.
    
    Args:
        user_id: The Telegram user ID
        user_level: The user's level (default: "Entry")
        user_video_number: The current video number
        user_state: The user's current state
        
    Returns:
        User record (existing or newly created)
    """
    try:
        existing_user = get_user(user_id)
        if existing_user:
            airtable_logger.log_system_event("user_already_exists", {
                "user_id": user_id
            })
            return existing_user
            
        user_data = {
            "Telegram ID": user_id,
            "Level": user_level,
            "Video Number": user_video_number,
            "State": user_state
        }
        
        new_user = users_table.create(user_data)
        
        if new_user:
            airtable_logger.log_system_event("user_created", {
                "user_id": user_id,
                "airtable_id": new_user.get('id'),
                "level": user_level
            })
            # Invalidate user cache
            user_cache.delete(f"get_user:{user_id}")
        else:
            airtable_logger.log_error("user_creation_failed", {
                "user_id": user_id
            })
            
        return new_user
        
    except Exception as e:
        airtable_logger.log_error("user_creation_error", {
            "user_id": user_id,
            "error": str(e)
        })
        return None

def update_user(user_data: UserRecord) -> bool:
    """
    Update user data in Airtable.
    
    Args:
        user_data: The user record to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create a copy of fields to avoid modifying the original
        fields_to_update = user_data['fields'].copy()
        
        # Remove computed fields that cannot be updated
        fields_to_remove = ["Updated At", "Created At"]
        for field in fields_to_remove:
            fields_to_update.pop(field, None)
        
        users_table.update(user_data['id'], fields_to_update)
        
        # Invalidate user cache
        telegram_id = fields_to_update.get('Telegram ID')
        if telegram_id:
            user_cache.delete(f"get_user:{telegram_id}")
        
        airtable_logger.log_system_event("user_updated", {
            "user_id": user_data.get('id'),
            "telegram_id": telegram_id
        })
        return True
        
    except Exception as e:
        airtable_logger.log_error("user_update_error", {
            "user_id": user_data.get('id', 'unknown'),
            "error": str(e)
        })
        return False

def create_message(message_text: str, role: str = "User", video_record_id: Optional[str] = None) -> Optional[MessageRecord]:
    """
    Create a new message record in the messages table.
    
    Args:
        message_text: The message content
        role: Role of the message sender (default: "User")
        video_record_id: Optional video record ID for linking
    
    Returns:
        Created message record or None if failed
    """
    try:
        if not messages_table:
            airtable_logger.log_error("messages_table_not_configured")
            return None
            
        message_data = {
            "Role": role,
            "Message": message_text
        }
        
        # Note: Video field linking temporarily disabled due to Airtable field configuration issues
        # The core message logging functionality works without video linking
        # TODO: Fix video field linking once Airtable schema is clarified
        
        message_record = messages_table.create(message_data)
        
        if message_record:
            message_id = message_record.get('id')
            
            airtable_logger.log_system_event("message_created", {
                "message_id": message_id,
                "role": role,
                "video_id": video_record_id
            })
            return message_record
        else:
            airtable_logger.log_error("message_creation_failed", {
                "role": role
            })
            return None
        
    except Exception as e:
        airtable_logger.log_error("message_creation_error", {
            "role": role,
            "video_id": video_record_id,
            "error": str(e)
        })
        return None

def extract_video_info(video_record: VideoRecord) -> VideoInfo:
    """
    Extract video information from Airtable record.
    
    Args:
        video_record: Video record from Airtable
        
    Returns:
        VideoInfo object with extracted data including record ID
    """
    fields = video_record.get('fields', {})
    return VideoInfo(
        title=fields.get('Title', ''),
        description=fields.get('Description', ''),
        question=fields.get('Question', ''),
        url=fields.get('YouTube Link', ''),
        level=fields.get('Level', ''),
        video_number=fields.get('Video Number', fields.get('# Video Number', 0)),
        understanding_benchmark=fields.get('Understanding Benchmark'),
        record_id=video_record.get('id')  # Include the Airtable record ID
    )



