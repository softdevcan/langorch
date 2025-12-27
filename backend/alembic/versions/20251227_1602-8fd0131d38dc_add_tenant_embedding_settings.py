"""add_tenant_embedding_settings

Revision ID: 8fd0131d38dc
Revises: c7094c3584af
Create Date: 2025-12-27 16:02:03.483581

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '8fd0131d38dc'
down_revision: Union[str, Sequence[str], None] = 'c7094c3584af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add embedding provider settings to tenants"""
    # Add embedding_provider column (default to 'openai' for backward compatibility)
    op.add_column(
        'tenants',
        sa.Column(
            'embedding_provider',
            sa.String(50),
            server_default='openai',
            nullable=False,
            comment='Embedding provider type (openai, ollama, claude, gemini)'
        )
    )

    # Add embedding_config column (JSONB for provider-specific configuration)
    op.add_column(
        'tenants',
        sa.Column(
            'embedding_config',
            JSONB(),
            nullable=True,
            comment='Provider-specific configuration (API keys, URLs, model settings)'
        )
    )

    # Create index on embedding_provider for faster lookups
    op.create_index(
        'ix_tenants_embedding_provider',
        'tenants',
        ['embedding_provider']
    )


def downgrade() -> None:
    """Downgrade schema - Remove embedding provider settings"""
    # Drop index
    op.drop_index('ix_tenants_embedding_provider', table_name='tenants')

    # Drop columns
    op.drop_column('tenants', 'embedding_config')
    op.drop_column('tenants', 'embedding_provider')
