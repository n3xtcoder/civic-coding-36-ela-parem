#!/usr/bin/env python3
"""
Test script to verify Google Sheets migration from Airtable.
Run this script to test the Google Sheets integration.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_config():
    """Test configuration validation."""
    print("Testing configuration...")
    try:
        from config import Config
        is_valid = Config.validate_config()
        print(f"✓ Configuration valid: {is_valid}")
        
        if not is_valid:
            print("❌ Missing required configuration:")
            required_fields = [
                Config.BOT_TOKEN,
                Config.GOOGLE_SHEETS_API_KEY,
                Config.GOOGLE_SHEETS_SPREADSHEET_ID,
                Config.MISTRAL_API_KEY
            ]
            field_names = ["BOT_TOKEN", "GOOGLE_SHEETS_API_KEY", "GOOGLE_SHEETS_SPREADSHEET_ID", "MISTRAL_API_KEY"]
            
            for field, name in zip(required_fields, field_names):
                if not field:
                    print(f"  - {name}")
        
        return is_valid
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_google_sheets_service():
    """Test Google Sheets service initialization."""
    print("\nTesting Google Sheets service...")
    try:
        from services.google_sheets_service import sheets_service
        
        if sheets_service.service:
            print("✓ Google Sheets service initialized successfully")
            return True
        else:
            print("❌ Google Sheets service failed to initialize")
            print("  - Check if GOOGLE_SHEETS_API_KEY is set")
            print("  - Verify GOOGLE_SHEETS_SPREADSHEET_ID is correct")
            print("  - Ensure spreadsheet is publicly readable")
            return False
    except Exception as e:
        print(f"❌ Google Sheets service test failed: {e}")
        return False

def test_imports():
    """Test that all imports work correctly."""
    print("\nTesting imports...")
    try:
        from google_sheets_service import get_user, create_user, update_user, create_message, get_videos, extract_video_info
        print("✓ All Google Sheets service imports successful")
        
        from main import Bot, Dispatcher
        print("✓ Main application imports successful")
        
        return True
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_api_key():
    """Test if API key is provided."""
    print("\nTesting API key...")
    api_key = os.getenv("GOOGLE_SHEETS_API_KEY")
    
    if api_key:
        print(f"✓ API key found: {api_key[:10]}...")
        return True
    else:
        print("❌ API key not found")
        print("  - Set GOOGLE_SHEETS_API_KEY in your .env file")
        print("  - Get API key from Google Cloud Console")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Google Sheets Migration")
    print("=" * 50)
    
    tests = [
        test_api_key,
        test_config,
        test_imports,
        test_google_sheets_service
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Google Sheets migration is ready.")
        print("\nNext steps:")
        print("1. Set up your Google Sheets with the required headers")
        print("2. Make the spreadsheet publicly readable")
        print("3. Add some test video data")
        print("4. Run the bot: python main.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
