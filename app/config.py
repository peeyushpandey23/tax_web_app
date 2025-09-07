import os
import logging
from typing import Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

# Configure logging
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Tax Advisor Application"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database Settings (Supabase) - using actual env var names
    DATABASE_URL: Optional[str] = None
    DATABASE_PASSWORD: Optional[str] = None
    DATABASE_KEY: Optional[str] = None
    
    # Alternative database settings (actual env var names)
    DB_URL: Optional[str] = None
    DB_PWD: Optional[str] = None
    DB_KEY: Optional[str] = None
    CONNECTION_STRING: Optional[str] = None
    
    # Gemini AI Settings
    GEMINI_API_KEY: Optional[str] = None
    
    # File Upload Settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list = [".pdf"]
    UPLOAD_FOLDER: str = "/tmp/uploads"
    
    # Security Settings
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    @model_validator(mode='after')
    def validate_database_settings(self):
        # Use alternative field names if main ones are empty
        if not self.DATABASE_URL and self.DB_URL:
            self.DATABASE_URL = self.DB_URL
        if not self.DATABASE_PASSWORD and self.DB_PWD:
            self.DATABASE_PASSWORD = self.DB_PWD
        if not self.DATABASE_KEY and self.DB_KEY:
            self.DATABASE_KEY = self.DB_KEY
            
        # Validate required fields - CONNECTION_STRING takes priority
        if self.CONNECTION_STRING:
            # If CONNECTION_STRING is provided, we don't need individual components
            logger.info("Using CONNECTION_STRING for database connection")
            return self
            
        # Otherwise validate individual components
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL or DB_URL is required (or provide CONNECTION_STRING)")
        if not self.DATABASE_PASSWORD:
            raise ValueError("DATABASE_PASSWORD or DB_PWD is required (or provide CONNECTION_STRING)")
        if not self.DATABASE_KEY:
            raise ValueError("DATABASE_KEY or DB_KEY is required (or provide CONNECTION_STRING)")
            
        return self
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }

# Create settings instance
settings = Settings()

