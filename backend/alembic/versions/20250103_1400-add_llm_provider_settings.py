"""add_llm_provider_settings_to_tenants

Revision ID: llm_provider_001
Revises: d87ddf8d05fb
Create Date: 2025-01-03 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'llm_provider_001'
down_revision: Union[str, Sequence[str], None] = 'd87ddf8d05fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add LLM provider settings to tenants"""
    # Add llm_provider column (default to 'ollama' for local usage)
    op.add_column(
        'tenants',
        sa.Column(
            'llm_provider',
            sa.String(50),
            server_default='ollama',
            nullable=False,
            comment='LLM provider type (openai, anthropic, ollama)'
        )
    )

    # Add llm_config column (JSONB for provider-specific configuration)
    op.add_column(
        'tenants',
        sa.Column(
            'llm_config',
            JSONB(),
            nullable=True,
            comment='LLM provider-specific configuration (API keys, URLs, model settings)'
        )
    )

    # Create index on llm_provider for faster lookups
    op.create_index(
        'ix_tenants_llm_provider',
        'tenants',
        ['llm_provider']
    )

    # Set default config for existing tenants (Ollama with llama3.2)
    op.execute("""
        UPDATE tenants
        SET llm_config = '{"model": "llama3.2", "base_url": "http://localhost:11434"}'::jsonb
        WHERE llm_config IS NULL
    """)


def downgrade() -> None:
    """Downgrade schema - Remove LLM provider settings"""
    # Drop index
    op.drop_index('ix_tenants_llm_provider', table_name='tenants')

    # Drop columns
    op.drop_column('tenants', 'llm_config')
    op.drop_column('tenants', 'llm_provider')
