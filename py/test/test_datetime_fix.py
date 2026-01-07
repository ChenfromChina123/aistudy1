#!/usr/bin/env python3
"""
Test script to verify the datetime serialization fix for UserSettings
"""

from datetime import datetime, UTC
from app import UserSettings, UserSettingsResponse

def test_datetime_serialization():
    """Test that datetime objects are properly serialized to strings"""
    
    # Create a mock UserSettings object with datetime fields
    user_settings = UserSettings(
        id=1,
        user_id=123,
        model_name="test-model",
        api_base="https://api.example.com",
        api_key="test-api-key",
        model_params='{"temperature": 0.7}',
        created_at=datetime(2025, 11, 9, 10, 5, 1, tzinfo=UTC),
        updated_at=datetime(2025, 11, 12, 9