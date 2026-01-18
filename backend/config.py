"""
Configuration management for backend service
"""
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    """Application settings"""

    # Note: Database configuration is loaded from ~/database_config.json
    # via DBConfigManager (shared with chat-history-crawler project)
    # Specify which database name to use from the config
    db_name_to_use: str = os.getenv("DB_NAME_TO_USE", "")

    # Zhipu AI
    zhipu_api_key: str = os.getenv("ZHIPU_API_KEY", "")
    zhipu_model: str = os.getenv("ZHIPU_MODEL", "glm-4-plus")

    # API Server
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))

    class Config:
        env_file = ".env"

settings = Settings()
