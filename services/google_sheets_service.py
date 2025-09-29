"""
Google Sheets service for managing data operations with caching and lean logging.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import Config
from models import VideoRecord, UserRecord, MessageRecord, VideoInfo, UserData, MessageData
from logger import main_logger

class GoogleSheetsService:
    """Service class for Google Sheets operations."""
    
    def __init__(self):
        """Initialize the Google Sheets service."""
        self.service = None
        self.spreadsheet_id = Config.GOOGLE_SHEETS_SPREADSHEET_ID
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize the Google Sheets API service."""
        try:
            # Check if API key is provided
            api_key = Config.GOOGLE_SHEETS_API_KEY
            if not api_key:
                main_logger.log_error("google_sheets_api_key_not_found", {
                    "api_key": "not_provided"
                })
                return
            
            # Build the service with API key
            self.service = build('sheets', 'v4', developerKey=api_key)
            
            main_logger.log_system_event("google_sheets_service_initialized", {
                "spreadsheet_id": self.spreadsheet_id,
                "auth_method": "api_key"
            })
            
        except Exception as e:
            main_logger.log_error("google_sheets_service_init_error", {
                "error": str(e)
            })
            self.service = None
    
    def _get_sheet_data(self, sheet_name: str, range_name: str = None) -> List[List[str]]:
        """
        Get data from a specific sheet.
        
        Args:
            sheet_name: Name of the sheet
            range_name: Optional range (e.g., 'A1:Z1000')
            
        Returns:
            List of rows from the sheet
        """
        if not self.service:
            main_logger.log_error("google_sheets_service_not_initialized")
            return []
        
        try:
            if range_name:
                range_str = f"{sheet_name}!{range_name}"
            else:
                range_str = sheet_name
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_str
            ).execute()
            
            values = result.get('values', [])
            main_logger.log_system_event("sheet_data_retrieved", {
                "sheet_name": sheet_name,
                "range": range_name,
                "row_count": len(values)
            })
            return values
            
        except HttpError as e:
            main_logger.log_error("sheet_data_retrieval_error", {
                "sheet_name": sheet_name,
                "range": range_name,
                "error": str(e)
            })
            return []
    
    def _append_to_sheet(self, sheet_name: str, values: List[List[str]]) -> bool:
        """
        Append data to a sheet.
        
        Args:
            sheet_name: Name of the sheet
            values: List of rows to append
            
        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            main_logger.log_error("google_sheets_service_not_initialized")
            return False
        
        try:
            body = {'values': values}
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A:Z",
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            main_logger.log_system_event("data_appended_to_sheet", {
                "sheet_name": sheet_name,
                "rows_added": len(values)
            })
            return True
            
        except HttpError as e:
            main_logger.log_error("sheet_append_error", {
                "sheet_name": sheet_name,
                "error": str(e)
            })
            return False
    
    def _update_sheet_row(self, sheet_name: str, row_index: int, values: List[str]) -> bool:
        """
        Update a specific row in a sheet.
        
        Args:
            sheet_name: Name of the sheet
            row_index: Row number to update (1-based)
            values: New values for the row
            
        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            main_logger.log_error("google_sheets_service_not_initialized")
            return False
        
        try:
            range_str = f"{sheet_name}!A{row_index}:Z{row_index}"
            body = {'values': [values]}
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_str,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            main_logger.log_system_event("sheet_row_updated", {
                "sheet_name": sheet_name,
                "row_index": row_index
            })
            return True
            
        except HttpError as e:
            main_logger.log_error("sheet_row_update_error", {
                "sheet_name": sheet_name,
                "row_index": row_index,
                "error": str(e)
            })
            return False
    
    def _find_row_by_column_value(self, sheet_name: str, column_index: int, search_value: str) -> Optional[int]:
        """
        Find a row by searching for a value in a specific column.
        
        Args:
            sheet_name: Name of the sheet
            column_index: Column index to search (0-based)
            search_value: Value to search for
            
        Returns:
            Row index (1-based) if found, None otherwise
        """
        data = self._get_sheet_data(sheet_name)
        if not data:
            return None
        
        # Skip header row
        for i, row in enumerate(data[1:], start=2):
            if len(row) > column_index and str(row[column_index]) == str(search_value):
                return i
        
        return None

# Initialize the service
sheets_service = GoogleSheetsService()

def get_videos(level: Optional[str] = None, video_number: Optional[int] = None) -> List[VideoRecord]:
    """
    Retrieve videos from Google Sheets based on level and video number.
    
    Args:
        level: The difficulty level to filter by
        video_number: The specific video number to filter by
        
    Returns:
        List of video records matching the criteria
    """
    try:
        # Get all video data
        data = sheets_service._get_sheet_data(Config.VIDEOS_SHEET_NAME)
        if not data:
            main_logger.log_error("videos_sheet_empty")
            return []
        
        # Assume first row is headers
        headers = data[0] if data else []
        videos = []
        
        # Convert sheet data to record format
        for i, row in enumerate(data[1:], start=2):  # Skip header, start from row 2
            if not row:  # Skip empty rows
                continue
                
            # Create a record-like structure similar to Airtable
            fields = {}
            for j, header in enumerate(headers):
                if j < len(row):
                    fields[header] = row[j]
                else:
                    fields[header] = ""
            
            # Add row number as ID
            record = {
                'id': str(i),
                'fields': fields
            }
            
            # Apply filters
            if level and video_number is not None:
                if (fields.get('Level', '') == level and 
                    (fields.get('Video Number', '') == str(video_number) or 
                     fields.get('# Video Number', '') == str(video_number))):
                    videos.append(record)
            elif level:
                if fields.get('Level', '') == level:
                    videos.append(record)
            else:
                videos.append(record)
        
        main_logger.log_system_event("videos_retrieved", {
            "level": level,
            "video_number": video_number,
            "count": len(videos)
        })
        
        return videos
        
    except Exception as e:
        main_logger.log_error("videos_retrieval_error", {
            "level": level,
            "video_number": video_number,
            "error": str(e)
        })
        return []

def get_user(user_id: int) -> Optional[UserRecord]:
    """
    Retrieve a user from Google Sheets by Telegram ID.
    
    Args:
        user_id: The Telegram user ID
        
    Returns:
        User record if found, None otherwise
    """
    try:
        # Get users sheet data
        data = sheets_service._get_sheet_data(Config.USERS_SHEET_NAME)
        if not data:
            main_logger.log_error("users_sheet_empty")
            return None
        
        headers = data[0] if data else []
        
        # Find Telegram ID column
        telegram_id_col = None
        for i, header in enumerate(headers):
            if 'Telegram ID' in header:
                telegram_id_col = i
                break
        
        if telegram_id_col is None:
            main_logger.log_error("telegram_id_column_not_found")
            return None
        
        # Search for user
        for i, row in enumerate(data[1:], start=2):  # Skip header
            if len(row) > telegram_id_col and str(row[telegram_id_col]) == str(user_id):
                # Create user record
                fields = {}
                for j, header in enumerate(headers):
                    if j < len(row):
                        fields[header] = row[j]
                    else:
                        fields[header] = ""
                
                user_record = {
                    'id': str(i),
                    'fields': fields
                }
                
                main_logger.log_system_event("user_found", {
                    "user_id": user_id,
                    "sheet_row": i
                })
                return user_record
        
        main_logger.log_system_event("user_not_found", {
            "user_id": user_id,
            "reason": "user_not_in_sheet"
        })
        return None
        
    except Exception as e:
        main_logger.log_error("user_retrieval_error", {
            "user_id": user_id,
            "error": str(e)
        })
        return None

def create_user(user_id: int, user_level: str = "Entry", user_video_number: Optional[int] = None, user_state: str = "") -> Optional[UserRecord]:
    """
    Create a new user in Google Sheets if they don't already exist.
    
    Args:
        user_id: The Telegram user ID
        user_level: The user's level (default: "Entry")
        user_video_number: The current video number
        user_state: The user's current state
        
    Returns:
        User record (existing or newly created)
    """
    try:
        # Check if user already exists
        existing_user = get_user(user_id)
        if existing_user:
            main_logger.log_system_event("user_already_exists", {
                "user_id": user_id
            })
            return existing_user
        
        # Prepare user data
        user_data = [
            str(user_id),  # Telegram ID
            user_level,    # Level
            str(user_video_number) if user_video_number is not None else "",  # Video Number
            user_state     # State
        ]
        
        # Append to users sheet
        success = sheets_service._append_to_sheet(Config.USERS_SHEET_NAME, [user_data])
        
        if success:
            # Get the newly created user
            new_user = get_user(user_id)
            if new_user:
                main_logger.log_system_event("user_created", {
                    "user_id": user_id,
                    "level": user_level
                })
                return new_user
        
        main_logger.log_error("user_creation_failed", {
            "user_id": user_id
        })
        return None
        
    except Exception as e:
        main_logger.log_error("user_creation_error", {
            "user_id": user_id,
            "error": str(e)
        })
        return None

def update_user(user_data: UserRecord) -> bool:
    """
    Update user data in Google Sheets.
    
    Args:
        user_data: The user record to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        row_index = int(user_data['id'])
        
        # Prepare updated data
        fields = user_data['fields']
        updated_row = [
            str(fields.get('Telegram ID', '')),
            fields.get('Level', ''),
            str(fields.get('Video Number', '')),
            fields.get('State', '')
        ]
        
        success = sheets_service._update_sheet_row(Config.USERS_SHEET_NAME, row_index, updated_row)
        
        if success:
            telegram_id = fields.get('Telegram ID')
            main_logger.log_system_event("user_updated", {
                "user_id": user_data.get('id'),
                "telegram_id": telegram_id
            })
        
        return success
        
    except Exception as e:
        main_logger.log_error("user_update_error", {
            "user_id": user_data.get('id', 'unknown'),
            "error": str(e)
        })
        return False

def create_message(message_text: str, role: str = "User", video_record_id: Optional[str] = None) -> Optional[MessageRecord]:
    """
    Create a new message record in the messages sheet.
    
    Args:
        message_text: The message content
        role: Role of the message sender (default: "User")
        video_record_id: Optional video record ID for linking
    
    Returns:
        Created message record or None if failed
    """
    try:
        # Prepare message data
        message_data = [
            role,           # Role
            message_text,   # Message
            video_record_id if video_record_id else ""  # Video ID
        ]
        
        # Append to messages sheet
        success = sheets_service._append_to_sheet(Config.MESSAGES_SHEET_NAME, [message_data])
        
        if success:
            # Get the newly created message (approximate)
            # In a real implementation, you might want to get the actual row number
            message_record = {
                'id': f"msg_{datetime.now().timestamp()}",
                'fields': {
                    'Role': role,
                    'Message': message_text,
                    'Video ID': video_record_id
                }
            }
            
            main_logger.log_system_event("message_created", {
                "message_id": message_record['id'],
                "role": role,
                "video_id": video_record_id
            })
            return message_record
        else:
            main_logger.log_error("message_creation_failed", {
                "role": role
            })
            return None
        
    except Exception as e:
        main_logger.log_error("message_creation_error", {
            "role": role,
            "video_id": video_record_id,
            "error": str(e)
        })
        return None

def extract_video_info(video_record: VideoRecord) -> VideoInfo:
    """
    Extract video information from Google Sheets record.
    
    Args:
        video_record: Video record from Google Sheets
        
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
        video_number=int(fields.get('Video Number', fields.get('# Video Number', 0)) or 0),
        understanding_benchmark=fields.get('Understanding Benchmark'),
        record_id=video_record.get('id')  # Include the Google Sheets row ID
    )
