import os
from typing import List, Union
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    APP_NAME: str = "RAG-Based Lead Segregation Agent"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:5173", "http://localhost:3000", "*"]

    # LLM Settings
    LLM_API_KEY: str = Field(default="")
    LLM_MODEL: str = "claude-3-5-sonnet-20241022"
    LLM_TEMPERATURE: float = 0.0
    LLM_PROVIDER: str = "auto"  # 'anthropic', 'mock', or 'auto' (mock if key empty)

    # Embedding & Vector Store
    EMBEDDING_MODEL: str = "BAAI/bge-small-en"
    EMBEDDING_PROVIDER: str = "fastembed"  # 'fastembed', 'mock'
    VECTOR_STORE: str = "chroma"  # 'chroma' or 'supabase'
    CHROMA_PERSIST_DIR: str = "./data/chroma"

    # Database
    DATABASE_URL: str = "sqlite:///./data/lead_agent.db"
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # Decision Gate Thresholds
    CONFIDENCE_THRESHOLD: float = 0.75
    REVIEW_THRESHOLD_MIN: float = 0.50
    UPLOAD_MAX_SIZE_MB: int = 25

    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        if isinstance(self.CORS_ORIGINS, str):
            if self.CORS_ORIGINS.startswith("["):
                import json
                try:
                    return json.loads(self.CORS_ORIGINS)
                except Exception:
                    pass
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return ["*"]


settings = Settings()

# Ensure local data directory exists
os.makedirs("./data", exist_ok=True)
os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
