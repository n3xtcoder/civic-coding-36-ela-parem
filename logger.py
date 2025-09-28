"""
Lean logging system for the Telegram bot application.
Only logs essential information to reduce noise and improve performance.
Supports both development and production logging configurations.
"""
import asyncio
import logging
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from functools import wraps
from pathlib import Path

class LeanLogger:
    """Lean logging system that only records necessary steps."""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Only add handler if not already configured
        if not self.logger.handlers:
            # Check if we should log to file
            log_file_path = os.getenv('LOG_FILE_PATH')
            environment = os.getenv('ENVIRONMENT', 'development')
            
            if log_file_path and environment == 'production':
                # Production: Log to file with rotation
                from logging.handlers import RotatingFileHandler
                
                # Ensure log directory exists
                log_dir = Path(log_file_path).parent
                log_dir.mkdir(parents=True, exist_ok=True)
                
                handler = RotatingFileHandler(
                    log_file_path,
                    maxBytes=10*1024*1024,  # 10MB
                    backupCount=5
                )
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                
                # Also log errors to stderr in production
                error_handler = logging.StreamHandler()
                error_handler.setLevel(logging.ERROR)
                error_handler.setFormatter(formatter)
                self.logger.addHandler(error_handler)
            else:
                # Development: Log to console
                handler = logging.StreamHandler()
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
    
    def log_user_action(self, user_id: int, action: str, details: Optional[Dict[str, Any]] = None):
        """Log essential user actions only."""
        log_data = {
            "user_id": user_id,
            "action": action,
            "timestamp": datetime.now().isoformat()
        }
        if details:
            log_data.update(details)
        
        self.logger.info(f"USER_ACTION: {json.dumps(log_data)}")
    
    def log_system_event(self, event: str, details: Optional[Dict[str, Any]] = None):
        """Log essential system events only."""
        log_data = {
            "event": event,
            "timestamp": datetime.now().isoformat()
        }
        if details:
            log_data.update(details)
        
        self.logger.info(f"SYSTEM_EVENT: {json.dumps(log_data)}")
    
    def log_error(self, error: str, context: Optional[Dict[str, Any]] = None):
        """Log errors with minimal context."""
        log_data = {
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        if context:
            log_data.update(context)
        
        self.logger.error(f"ERROR: {json.dumps(log_data)}")
    
    def log_performance(self, operation: str, duration_ms: float, details: Optional[Dict[str, Any]] = None):
        """Log performance metrics for slow operations."""
        if duration_ms > 100:  # Only log if operation takes more than 100ms
            log_data = {
                "operation": operation,
                "duration_ms": duration_ms,
                "timestamp": datetime.now().isoformat()
            }
            if details:
                log_data.update(details)
            
            self.logger.warning(f"PERFORMANCE: {json.dumps(log_data)}")

def performance_monitor(operation_name: str):
    """Decorator to monitor performance of functions."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger = LeanLogger(func.__module__)
                logger.log_performance(operation_name, duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger = LeanLogger(func.__module__)
                logger.log_performance(f"{operation_name}_error", duration_ms, {"error": str(e)})
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger = LeanLogger(func.__module__)
                logger.log_performance(operation_name, duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger = LeanLogger(func.__module__)
                logger.log_performance(f"{operation_name}_error", duration_ms, {"error": str(e)})
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Global logger instances
main_logger = LeanLogger("main")
airtable_logger = LeanLogger("airtable")
conversation_logger = LeanLogger("conversation")
