"""add_basic_rag_tables_v0_3

Revision ID: 249c335ac639
Revises: 8fd0131d38dc
Create Date: 2025-12-28 00:10:55.190750

Add tables for Version 0.3: Basic RAG & LLM Integration
- llm_conversations: Conversation threads
- llm_messages: Conversation messages
- llm_operations: Track document operations (summarize, ask, transform)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '249c335ac639'
down_revision: Union[str, Sequence[str], None] = '8fd0131d38dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Create llm_conversations table
    op.create_table(
        'llm_conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.Text, nullable=True),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
    )

    op.create_index('idx_llm_conversations_tenant', 'llm_conversations', ['tenant_id'])
    op.create_index('idx_llm_conversations_user', 'llm_conversations', ['user_id'])
    op.create_index('idx_llm_conversations_document', 'llm_conversations', ['document_id'])

    # Create llm_messages table
    op.create_table(
        'llm_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.Text, nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['conversation_id'], ['llm_conversations.id'], ondelete='CASCADE'),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system')", name='check_message_role'),
    )

    op.create_index('idx_llm_messages_conversation', 'llm_messages', ['conversation_id'])
    op.create_index('idx_llm_messages_created', 'llm_messages', ['created_at'])

    # Create llm_operations table
    op.create_table(
        'llm_operations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('operation_type', sa.Text, nullable=False),
        sa.Column('input_data', postgresql.JSONB, nullable=False),
        sa.Column('output_data', postgresql.JSONB, nullable=True),
        sa.Column('model_used', sa.Text, nullable=True),
        sa.Column('tokens_used', sa.Integer, nullable=True),
        sa.Column('cost_estimate', sa.DECIMAL(10, 6), nullable=True),
        sa.Column('status', sa.Text, nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.CheckConstraint("operation_type IN ('summarize', 'ask', 'transform')", name='check_operation_type'),
        sa.CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name='check_operation_status'),
    )

    op.create_index('idx_llm_operations_tenant', 'llm_operations', ['tenant_id'])
    op.create_index('idx_llm_operations_user', 'llm_operations', ['user_id'])
    op.create_index('idx_llm_operations_document', 'llm_operations', ['document_id'])
    op.create_index('idx_llm_operations_status', 'llm_operations', ['status'])

    # Enable RLS on all tables
    op.execute('ALTER TABLE llm_conversations ENABLE ROW LEVEL SECURITY')
    op.execute("""
        CREATE POLICY tenant_isolation_llm_conversations ON llm_conversations
        USING (tenant_id::text = current_setting('app.current_tenant', true))
    """)

    op.execute('ALTER TABLE llm_messages ENABLE ROW LEVEL SECURITY')
    op.execute("""
        CREATE POLICY tenant_isolation_llm_messages ON llm_messages
        USING (
            conversation_id IN (
                SELECT id FROM llm_conversations
                WHERE tenant_id::text = current_setting('app.current_tenant', true)
            )
        )
    """)

    op.execute('ALTER TABLE llm_operations ENABLE ROW LEVEL SECURITY')
    op.execute("""
        CREATE POLICY tenant_isolation_llm_operations ON llm_operations
        USING (tenant_id::text = current_setting('app.current_tenant', true))
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('llm_operations')
    op.drop_table('llm_messages')
    op.drop_table('llm_conversations')
