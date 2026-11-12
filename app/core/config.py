import os
from pathlib import Path
from typing import List, Union, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Serverless execution environment detection (e.g. Vercel, AWS Lambda)
IS_SERVERLESS: bool = bool(
    os.environ.get("VERCEL")
    or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    or os.environ.get("LAMBDA_TASK_ROOT")
)

# Base default directories depending on environment
_DEFAULT_DATA_DIR = Path("/tmp/data" if IS_SERVERLESS else "./data")
_DEFAULT_MODEL_CACHE = Path("/tmp/model_cache" if IS_SERVERLESS else "./data/model_cache")
_DEFAULT_CHROMA_DIR = Path("/tmp/chroma" if IS_SERVERLESS else "./data/chroma")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    APP_NAME: str = "RAG-Based Lead Segregation Agent"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")
    IS_SERVERLESS: bool = IS_SERVERLESS
    HOST: str = "0.0.0.0"
    PORT: int = Field(default_factory=lambda: int(os.environ.get("PORT", "8000")))
    CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:5173", "http://localhost:3000", "*"]

    # LLM Settings
    LLM_API_KEY: str = Field(default="")
    LLM_MODEL: str = "claude-3-5-sonnet-20241022"
    LLM_TEMPERATURE: float = 0.0
    LLM_PROVIDER: str = "auto"  # 'anthropic', 'mock', or 'auto' (mock if key empty)

    # Embedding & Vector Store
    EMBEDDING_MODEL: str = "BAAI/bge-small-en"
    EMBEDDING_PROVIDER: str = "fastembed"  # 'fastembed', 'mock'
    VECTOR_STORE: str = os.environ.get("VECTOR_STORE", "chroma")  # 'chroma', 'pgvector', 'supabase'
    CHROMA_PERSIST_DIR: str = os.environ.get("CHROMA_PERSIST_DIR", str(_DEFAULT_CHROMA_DIR))
    FASTEMBED_CACHE_PATH: str = os.environ.get("FASTEMBED_CACHE_PATH", str(_DEFAULT_MODEL_CACHE))
    MODEL_CACHE_DIR: str = os.environ.get("MODEL_CACHE_DIR", str(_DEFAULT_MODEL_CACHE))

    # Database
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./data/lead_agent.db")
    SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")

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

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")


settings = Settings()

# Set environment variables for libraries that read from env
os.environ.setdefault("FASTEMBED_CACHE_PATH", settings.FASTEMBED_CACHE_PATH)
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")


def safe_ensure_dir(path_str: Union[str, Path]) -> Optional[Path]:
    """Safely creates directory if writable without crashing on read-only serverless filesystems."""
    try:
        p = Path(path_str)
        p.mkdir(parents=True, exist_ok=True)
        return p
    except (OSError, PermissionError):
        return None


# Only attempt creating local storage directories if not running in read-only serverless mode
if not settings.IS_SERVERLESS and not settings.is_production:
    safe_ensure_dir("./data")
    safe_ensure_dir(settings.CHROMA_PERSIST_DIR)
    safe_ensure_dir(settings.FASTEMBED_CACHE_PATH)
else:
    # On serverless, ensure the writable /tmp cache exists
    safe_ensure_dir(settings.FASTEMBED_CACHE_PATH)

