"""
Settings schemas for API requests/responses
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from app.services.embedding_providers.base import ProviderType


class EmbeddingProviderUpdate(BaseModel):
    """
    Request schema for updating embedding provider settings
    """
    provider: ProviderType = Field(
        ...,
        description="Embedding provider type"
    )
    model: str = Field(
        ...,
        description="Model name (e.g., 'text-embedding-3-small' for OpenAI)"
    )
    api_key: Optional[str] = Field(
        None,
        description="API key (for OpenAI, Claude, Gemini)"
    )
    base_url: Optional[str] = Field(
        None,
        description="Base URL (for Ollama or custom endpoints)"
    )

    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate base URL format"""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Base URL must start with http:// or https://')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "api_key": "sk-..."
            }
        }


class EmbeddingProviderResponse(BaseModel):
    """
    Response schema for embedding provider settings
    """
    provider: ProviderType = Field(
        ...,
        description="Embedding provider type"
    )
    model: str = Field(
        ...,
        description="Model name"
    )
    dimensions: int = Field(
        ...,
        description="Embedding vector dimensions"
    )
    base_url: Optional[str] = Field(
        None,
        description="Base URL (for Ollama)"
    )
    has_api_key: bool = Field(
        ...,
        description="Whether an API key is configured (doesn't expose the key)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "dimensions": 1536,
                "base_url": None,
                "has_api_key": True
            }
        }


class EmbeddingProviderTest(BaseModel):
    """
    Request schema for testing embedding provider connection
    """
    provider: ProviderType = Field(
        ...,
        description="Embedding provider type to test"
    )
    model: str = Field(
        ...,
        description="Model name"
    )
    api_key: Optional[str] = Field(
        None,
        description="API key (for OpenAI, Claude, Gemini)"
    )
    base_url: Optional[str] = Field(
        None,
        description="Base URL (for Ollama)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "provider": "ollama",
                "model": "nomic-embed-text",
                "base_url": "http://localhost:11434"
            }
        }


class EmbeddingProviderTestResponse(BaseModel):
    """
    Response schema for provider connection test
    """
    success: bool = Field(
        ...,
        description="Whether the connection test was successful"
    )
    message: str = Field(
        ...,
        description="Result message"
    )
    dimensions: Optional[int] = Field(
        None,
        description="Detected embedding dimensions (if successful)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Successfully connected to Ollama and generated test embedding",
                "dimensions": 768
            }
        }
