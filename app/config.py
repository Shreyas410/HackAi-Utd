"""
Configuration settings for the learning system.
Uses environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    app_name: str = "Personalised Learning System"
    debug: bool = False
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./learning_system.db"
    
    # External APIs
    # Gemini API key - required for production, optional for testing (uses mocks)
    gemini_api_key: Optional[str] = None
    
    # YouTube Data API v3 key - for verified video links
    # Get from: https://console.cloud.google.com/apis/credentials
    # Free tier: 10,000 units/day (100 searches/day)
    youtube_api_key: Optional[str] = None
    
    # Session settings
    session_expiry_hours: int = 24
    
    # Quiz settings
    min_quiz_questions: int = 5
    max_quiz_questions: int = 10
    
    # Classification thresholds
    beginner_threshold: float = 2.5
    intermediate_threshold: float = 4.0
    
    # Quiz score thresholds for level adjustment
    upgrade_score_threshold: float = 0.85
    downgrade_score_threshold: float = 0.4
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


# Skill configurations - can be extended by adding new JSON files
SKILLS_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "data", "skills")
CONCEPT_MAPS_DIR = os.path.join(os.path.dirname(__file__), "data", "concept_maps")
RESOURCES_FILE = os.path.join(os.path.dirname(__file__), "data", "resources.json")
