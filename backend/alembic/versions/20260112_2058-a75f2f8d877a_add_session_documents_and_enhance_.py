"""add_session_documents_and_enhance_metadata_v0_4_1

Revision ID: a75f2f8d877a
Revises: 2624a808eb9b
Create Date: 2026-01-12 20:58:00.793655

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a75f2f8d877a'
down_revision: Union[str, Sequence[str], None] = '2624a808eb9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add session_documents table and standardize session metadata for v0.4.1."""

    # 1. Create session_documents table
    op.create_table(
        'session_documents',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('added_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['conversation_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'document_id', name='uq_session_document')
    )

    # 2. Create indexes for performance
    op.create_index('idx_session_documents_session', 'session_documents', ['session_id'])
    op.create_index('idx_session_documents_document', 'session_documents', ['document_id'])
    op.create_index('idx_session_documents_active', 'session_documents', ['session_id', 'is_active'])

    # 3. Enable RLS on session_documents
    op.execute("ALTER TABLE session_documents ENABLE ROW LEVEL SECURITY;")

    # 4. Create RLS policy for session_documents (tenant isolation through session)
    op.execute("""
        CREATE POLICY tenant_isolation_session_documents ON session_documents
        USING (
            session_id IN (
                SELECT id FROM conversation_sessions
                WHERE tenant_id::text = current_setting('app.current_tenant', true)
            )
        );
    """)

    # 5. Update existing sessions with default metadata structure
    # Note: session_metadata is JSON type, so we cast to/from jsonb for the operation
    op.execute("""
        UPDATE conversation_sessions
        SET session_metadata = (
            COALESCE(session_metadata::jsonb, '{}'::jsonb)
            || jsonb_build_object(
                'mode', 'auto',
                'document_context', jsonb_build_object(
                    'active_document_ids', '[]'::jsonb,
                    'last_upload_at', null,
                    'total_documents', 0,
                    'total_chunks', 0
                ),
                'routing_preferences', jsonb_build_object(
                    'auto_route', true,
                    'prefer_rag_when_available', true
                ),
                'conversation_summary', jsonb_build_object(
                    'topics', '[]'::jsonb,
                    'last_summary', null,
                    'message_count_at_summary', 0
                )
            )
        )::json
        WHERE session_metadata IS NULL
           OR (session_metadata::jsonb)->>'mode' IS NULL;
    """)


def downgrade() -> None:
    """Downgrade schema - Remove session_documents table and metadata structure."""

    # Drop RLS policy
    op.execute("DROP POLICY IF EXISTS tenant_isolation_session_documents ON session_documents;")

    # Drop indexes
    op.drop_index('idx_session_documents_active', 'session_documents')
    op.drop_index('idx_session_documents_document', 'session_documents')
    op.drop_index('idx_session_documents_session', 'session_documents')

    # Drop table
    op.drop_table('session_documents')

    # Note: We don't remove the metadata fields from existing sessions
    # as it's safer to leave them (they'll be ignored by the old code)
