"""
Conversation service for AI-powered assessments and interactions with lean logging.
Uses Mistral AI for intelligent conversation handling.
"""
import json
from typing import Dict, Any, Optional
from mistralai import Mistral
from config import Config
from models import AssessmentResult
from logger import conversation_logger

# Initialize Mistral client
client = Mistral(api_key=Config.MISTRAL_API_KEY)

def define_placement_group(question: str, answer: str) -> str:
    """
    Uses Mistral AI to determine the placement group ("Beginner", "Intermediate", or "Advanced")
    based on the provided question and answer.

    Args:
        question: The placement test question
        answer: The user's answer

    Returns:
        One of "Beginner", "Intermediate", or "Advanced"

    Raises:
        ValueError: If the model's response is not one of the expected groups
    """
    try:
        system_prompt = Config.AI_PROMPTS["PLACEMENT_SYSTEM"]
        
        response = client.chat.complete(
            model="ministral-8b-2410",
            messages=[
                {
                    "role": "system",
                    "content": f"{system_prompt} Question: {question}"
                },
                {"role": "user", "content": answer},
            ],
            max_tokens=2,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        valid_groups = {"Beginner", "Intermediate", "Advanced"}
        
        if result not in valid_groups:
            raise ValueError(f"Unexpected placement group: {result}")
            
        conversation_logger.log_system_event("placement_assessment_completed", {
            "result": result,
            "question_length": len(question),
            "answer_length": len(answer)
        })
        return result
        
    except Exception as e:
        conversation_logger.log_error("placement_assessment_error", {
            "error": str(e),
            "question_length": len(question),
            "answer_length": len(answer)
        })
        raise

def assess_video_response(question: str, user_answer: str, context: Optional[str] = None, conversation_history: Optional[str] = None) -> AssessmentResult:
    """
    Uses Mistral AI to assess a user's response to a video question with conversation context.
    
    Args:
        question: The question asked about the video
        user_answer: The user's response
        context: Optional context or expected understanding
        conversation_history: Optional conversation history for continuity
        
    Returns:
        AssessmentResult object with feedback
    """
    try:
        system_prompt = Config.AI_PROMPTS["VIDEO_ASSESSMENT_SYSTEM"]
        
        # Build context and conversation sections
        context_section = f"\nContext: {context}" if context else ""
        conversation_section = f"\nPrevious conversation:\n{conversation_history}" if conversation_history else ""
        
        user_prompt = Config.AI_PROMPTS["VIDEO_ASSESSMENT_USER_TEMPLATE"].format(
            question=question,
            user_answer=user_answer,
            context_section=context_section,
            conversation_section=conversation_section
        )
        
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        result = response.choices[0].message.content.strip()
        
        # Clean up the response if it's wrapped in markdown code blocks
        if result.startswith('```json'):
            # Remove ```json and ``` wrapper
            result = result[7:]  # Remove ```json
            if result.endswith('```'):
                result = result[:-3]  # Remove trailing ```
            result = result.strip()
        elif result.startswith('```'):
            # Remove generic ``` wrapper
            result = result[3:]
            if result.endswith('```'):
                result = result[:-3]
            result = result.strip()
        
        # Try to parse JSON response
        try:
            parsed_result = json.loads(result)
            feedback = parsed_result.get("feedback", result)
            conversation_logger.log_system_event("video_assessment_completed", {
                "has_context": bool(context),
                "has_conversation_history": bool(conversation_history),
                "question_length": len(question),
                "answer_length": len(user_answer)
            })
            return AssessmentResult(feedback=feedback)
        except json.JSONDecodeError:
            conversation_logger.log_system_event("video_assessment_json_fallback", {
                "raw_response_length": len(result)
            })
            return AssessmentResult(feedback=result)
            
    except Exception as e:
        conversation_logger.log_error("video_assessment_error", {
            "error": str(e),
            "question_length": len(question),
            "answer_length": len(user_answer)
        })
        # Fallback response if Mistral AI fails
        return AssessmentResult(
            feedback=Config.AI_PROMPTS["FALLBACK_RESPONSE"]
        )
