"""
Configuration management for the Telegram bot application.
"""
import os
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the application."""
    
    # Bot configuration
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # Airtable configuration
    AIRTABLE_API_KEY: str = os.getenv("AIRTABLE_API_KEY", "")
    AIRTABLE_BASE_ID: str = os.getenv("AIRTABLE_BASE_ID", "")
    VIDEOS_TABLE_ID: str = os.getenv("VIDEOS_TABLE_ID", "")
    USERS_TABLE_ID: str = os.getenv("USERS_TABLE_ID", "")
    MESSAGES_TABLE_ID: str = os.getenv("MESSAGES_TABLE_ID", "")
    
    # Mistral AI configuration
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    
    # Bot behavior constants
    VIDEO_WAIT_TIME: int = 10  # seconds to wait before asking question
    MAX_VIDEOS_PER_LEVEL: int = 2
    
    # User states
    USER_STATES = {
        "PLACEMENT_TEST": "Placement Test",
        "SHOWING_VIDEO": "Showing Video", 
        "WAITING_FOR_RESPONSE": "Waiting for Response",
        "CHAT_MODE": "Chat Mode",
        "COURSE_OVERVIEW": "Course Overview"
    }
    
    # User levels
    USER_LEVELS = {
        "ENTRY": "Entry",
        "BEGINNER": "Beginner",
        "INTERMEDIATE": "Intermediate", 
        "ADVANCED": "Advanced"
    }
    
    # Level progression
    LEVEL_PROGRESSION: Dict[str, str] = {
        "Beginner": "Intermediate",
        "Intermediate": "Advanced",
        "Advanced": "Advanced"  # Stay at Advanced level
    }
    
    # Bot messages
    MESSAGES = {
        "WELCOME_NOT_FOUND": "Keine Willkommensnachricht gefunden.",
        "USER_NOT_FOUND": "Benutzer nicht gefunden.",
        "START_BOT_FIRST": "Bitte starte den Bot mit /start",
        "VIDEO_NOT_FOUND": "Entschuldigung, das Video konnte nicht gefunden werden.",
        "ALREADY_REGISTERED": "Du bist bereits registriert.",
        "VIDEO_PROCESSING": "Bitte warte, das Video wird gerade verarbeitet...",
        "NEXT_VIDEO_LOADING": "Nächstes Video wird geladen...",
        "VIDEO_LOADING": "Perfekt! Video wird geladen...",
        "CONGRATULATIONS": "🎉 Glückwunsch! Du bist jetzt auf dem {level} Level!",
        "NEXT_VIDEO_START": "Super! Dann starten wir mit dem nächsten Video!",
        "READY_BUTTON": "🚀 Ja!",
        "UNDERSTOOD_BUTTON": "Verstanden!",
        "OVERVIEW_BUTTON": "📋 Kursübersicht"
    }
    
    # AI Prompts for Mistral AI
    AI_PROMPTS = {
        "PLACEMENT_SYSTEM": (
            "You are a placement test evaluator. "
            "Given a question and a user's answer, respond with ONLY ONE WORD: "
            "\"Beginner\", \"Intermediate\", or \"Advanced\". "
            "Do not include any explanation or extra text."
        ),
        "VIDEO_ASSESSMENT_SYSTEM": (
            "You are an educational assistant AI. Help the user improve their understanding of the video content. "
            "Engage with the user answer in a short chat style. Stay positive and encouraging. "
            "Finish with a question to the user to deepen their understanding."
        ),
        "VIDEO_ASSESSMENT_USER_TEMPLATE": """
        Question: {question}
        User's Answer: {user_answer}
        {context_section}
        {conversation_section}
        
        Please provide a JSON response with the following structure:
        {{
            "feedback": "<constructive feedback about their response>"
        }}
        """,
        "FALLBACK_RESPONSE": "Thank you for your response. We're having technical difficulties with assessment right now."
    }
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate that all required configuration is present."""
        required_fields = [
            cls.BOT_TOKEN,
            cls.AIRTABLE_API_KEY,
            cls.AIRTABLE_BASE_ID,
            cls.VIDEOS_TABLE_ID,
            cls.USERS_TABLE_ID,
            cls.MESSAGES_TABLE_ID,
            cls.MISTRAL_API_KEY
        ]
        return all(field for field in required_fields)
