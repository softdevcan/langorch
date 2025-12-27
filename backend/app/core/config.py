from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "LangOrch"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_VERSION: str = "0.1.0"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "langorch"
    POSTGRES_PASSWORD: str = "changeme_postgres_password"
    POSTGRES_DB: str = "langorch"
    DATABASE_URL: str = ""

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_URL: str = ""

    # Security
    SECRET_KEY: str = "changeme_secret_key_at_least_32_characters"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # HashiCorp Vault
    VAULT_ADDR: str = "http://localhost:8200"
    VAULT_TOKEN: str = "dev-root-token"
    VAULT_MOUNT_POINT: str = "secret"
    VAULT_TENANT_PATH: str = "tenants"  # secret/tenants/{tenant_id}

    # Qdrant Vector Store
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""  # Optional for local dev
    QDRANT_COLLECTION_NAME: str = "documents"
    QDRANT_URL: str = ""

    # Document Processing
    CHUNK_SIZE: int = 1000  # Characters per chunk
    CHUNK_OVERLAP: int = 200  # Overlap between chunks
    MAX_FILE_SIZE_MB: int = 50  # Maximum file upload size
    EMBEDDING_MODEL: str = "text-embedding-3-small"  # OpenAI embedding model
    EMBEDDING_DIMENSIONS: int = 1536  # Embedding vector dimensions

    # OpenAI (Fallback when Vault is not available)
    OPENAI_API_KEY: str = ""  # Fallback API key for development

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str, info) -> str:
        """Construct database URL if not provided"""
        if v:
            return v
        return (
            f"postgresql+asyncpg://{info.data['POSTGRES_USER']}:"
            f"{info.data['POSTGRES_PASSWORD']}@{info.data['POSTGRES_HOST']}:"
            f"{info.data['POSTGRES_PORT']}/{info.data['POSTGRES_DB']}"
        )

    @field_validator("QDRANT_URL", mode="before")
    @classmethod
    def assemble_qdrant_url(cls, v: str, info) -> str:
        """Construct Qdrant URL if not provided"""
        if v:
            return v
        return f"http://{info.data['QDRANT_HOST']}:{info.data['QDRANT_PORT']}"


settings = Settings()
