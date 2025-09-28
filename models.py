"""
Data models and type definitions for the Telegram bot application.
"""
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

class UserState(Enum):
    """Enum for user states."""
    PLACEMENT_TEST = "Placement Test"
    SHOWING_VIDEO = "Showing Video"
    WAITING_FOR_RESPONSE = "Waiting for Response"
    CHAT_MODE = "Chat Mode"
    COURSE_OVERVIEW = "Course Overview"

class UserLevel(Enum):
    """Enum for user levels."""
    ENTRY = "Entry"
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"

@dataclass
class VideoInfo:
    """Data class for video information."""
    title: str
    description: str
    question: str
    url: str
    level: str
    video_number: int
    understanding_benchmark: Optional[str] = None
    record_id: Optional[str] = None  # Airtable record ID for linking

@dataclass
class UserData:
    """Data class for user information."""
    telegram_id: int
    level: str
    video_number: int
    state: str
    record_id: Optional[str] = None

@dataclass
class MessageData:
    """Data class for message information."""
    user_id: int
    message_text: str
    role: str
    video_info: Optional[Dict[str, Any]] = None
    message_id: Optional[str] = None

@dataclass
class AssessmentResult:
    """Data class for assessment results."""
    feedback: str
    level: Optional[str] = None
    confidence: Optional[float] = None

@dataclass
class ConversationMessage:
    """Data class for a single message in conversation history."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: float
    message_id: Optional[str] = None  # Airtable message record ID

@dataclass
class VideoConversationContext:
    """Data class for conversation context within a video."""
    video_record_id: str
    video_title: str
    video_question: str
    understanding_benchmark: Optional[str]
    conversation_history: List[ConversationMessage]
    created_at: float
    
    def add_message(self, role: str, content: str, message_id: Optional[str] = None) -> None:
        """Add a message to the conversation history."""
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=time.time(),
            message_id=message_id
        )
        self.conversation_history.append(message)
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation for context."""
        if not self.conversation_history:
            return ""
        
        summary_parts = []
        for msg in self.conversation_history[-5:]:  # Last 5 messages for context
            role_label = "User" if msg.role == "user" else "Assistant"
            summary_parts.append(f"{role_label}: {msg.content}")
        
        return "\n".join(summary_parts)
    
    def clear_history(self) -> None:
        """Clear conversation history while keeping video context."""
        self.conversation_history.clear()

# Type aliases for better code readability
AirtableRecord = Dict[str, Any]
AirtableFields = Dict[str, Any]
VideoRecord = Dict[str, Any]
UserRecord = Dict[str, Any]
MessageRecord = Dict[str, Any]
