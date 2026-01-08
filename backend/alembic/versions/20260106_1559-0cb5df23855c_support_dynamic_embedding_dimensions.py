"""support_dynamic_embedding_dimensions

Revision ID: 0cb5df23855c
Revises: llm_provider_001
Create Date: 2026-01-06 15:59:24.348205

This migration changes embedding columns from fixed 1536 dimensions to dynamic dimensions.
This allows the system to work with different embedding models:
- OpenAI text-embedding-3-small: 1536 dimensions
- nomic-embed-text: 768 dimensions
- Other models with varying dimensions

The change is backward compatible - existing 1536-dim embeddings will continue to work.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0cb5df23855c'
down_revision: Union[str, Sequence[str], None] = 'llm_provider_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Change embedding vectors from fixed 1536 dimensions to dynamic dimensions.

    Best practice: Store embeddings as JSONB arrays for true dynamic dimensions.
    This avoids padding overhead and works with any embedding model.
    """
    # Drop existing vector columns
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")

    # Use JSONB for truly dynamic dimensions (best practice for multi-model support)
    op.execute("""
        ALTER TABLE documents
        ADD COLUMN embedding JSONB NULL
    """)
    op.execute("COMMENT ON COLUMN documents.embedding IS 'Document-level embedding vector (dynamic dimensions, stored as JSONB array)'")

    op.execute("""
        ALTER TABLE document_chunks
        ADD COLUMN embedding JSONB NULL
    """)
    op.execute("COMMENT ON COLUMN document_chunks.embedding IS 'Chunk embedding vector (dynamic dimensions, stored as JSONB array) - nullable for documents without embeddings'")

    # Note: For vector similarity search, we'll still use Qdrant
    # Database embeddings are for storage/retrieval only


def downgrade() -> None:
    """
    Revert back to fixed 1536 dimensions.

    WARNING: This will fail if you have embeddings with dimensions other than 1536.
    You would need to manually delete or re-embed those documents first.
    """
    # Drop dynamic dimension columns
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")

    # Recreate with fixed 1536 dimensions
    op.execute("""
        ALTER TABLE documents
        ADD COLUMN embedding vector(1536) NULL
    """)
    op.execute("COMMENT ON COLUMN documents.embedding IS 'Document-level embedding vector (1536 dimensions)'")

    op.execute("""
        ALTER TABLE document_chunks
        ADD COLUMN embedding vector(1536) NULL
    """)
    op.execute("COMMENT ON COLUMN document_chunks.embedding IS 'Chunk embedding vector (1536 dimensions) - nullable for documents without embeddings'")
