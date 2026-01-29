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

    # DeepSeek AI
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_model_r1: str = os.getenv("DEEPSEEK_MODEL_R1", "deepseek-reasoner")
    deepseek_model_chat: str = os.getenv("DEEPSEEK_MODEL_CHAT", "deepseek-chat")
    deepseek_temperature_evidence: float = float(os.getenv("DEEPSEEK_TEMP_EVIDENCE", "0.3"))
    deepseek_temperature_inference: float = float(os.getenv("DEEPSEEK_TEMP_INFERENCE", "0.7"))

    # AI Analysis Settings
    ai_cache_ttl_days: int = int(os.getenv("AI_CACHE_TTL_DAYS", "30"))
    ai_enable_cache: bool = os.getenv("AI_ENABLE_CACHE", "true").lower() == "true"

    # API Server
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))

    class Config:
        env_file = ".env"
        extra = "ignore"  # 允许额外的环境变量

settings = Settings()
