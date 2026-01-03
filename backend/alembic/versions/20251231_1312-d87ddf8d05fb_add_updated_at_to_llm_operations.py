"""add_updated_at_to_llm_operations

Revision ID: d87ddf8d05fb
Revises: 249c335ac639
Create Date: 2025-12-31 13:12:24.183810

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd87ddf8d05fb'
down_revision: Union[str, Sequence[str], None] = '249c335ac639'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add updated_at column to llm_operations table."""
    op.add_column('llm_operations',
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False)
    )


def downgrade() -> None:
    """Remove updated_at column from llm_operations table."""
    op.drop_column('llm_operations', 'updated_at')
