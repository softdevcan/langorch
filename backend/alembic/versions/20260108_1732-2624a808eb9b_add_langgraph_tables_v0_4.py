"""add_langgraph_tables_v0_4

Revision ID: 2624a808eb9b
Revises: 0cb5df23855c
Create Date: 2026-01-08 17:32:51.238604

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2624a808eb9b'
down_revision: Union[str, Sequence[str], None] = '0cb5df23855c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add LangGraph v0.4 tables."""

    # 1. workflows table
    op.create_table(
        'workflows',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('workflow_config', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_workflows_tenant', 'workflows', ['tenant_id'])
    op.create_index('idx_workflows_active', 'workflows', ['is_active'])

    # 2. workflow_executions table
    op.create_table(
        'workflow_executions',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=True),
        sa.Column('thread_id', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('output_data', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('running', 'completed', 'failed', 'interrupted')", name='workflow_executions_status_check')
    )
    op.create_index('idx_workflow_executions_tenant', 'workflow_executions', ['tenant_id'])
    op.create_index('idx_workflow_executions_thread', 'workflow_executions', ['thread_id'])
    op.create_index('idx_workflow_executions_status', 'workflow_executions', ['status'])

    # 3. conversation_sessions table
    op.create_table(
        'conversation_sessions',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=True),
        sa.Column('thread_id', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('session_metadata', sa.JSON(), server_default=sa.text("'{}'"), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('thread_id')
    )
    op.create_index('idx_conversation_sessions_tenant', 'conversation_sessions', ['tenant_id'])
    op.create_index('idx_conversation_sessions_user', 'conversation_sessions', ['user_id'])
    op.create_index('idx_conversation_sessions_thread', 'conversation_sessions', ['thread_id'])

    # 4. messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_metadata', sa.JSON(), server_default=sa.text("'{}'"), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['conversation_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system')", name='messages_role_check')
    )
    op.create_index('idx_messages_session', 'messages', ['session_id'])
    op.create_index('idx_messages_created', 'messages', ['created_at'])

    # 5. hitl_approvals table
    op.create_table(
        'hitl_approvals',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('execution_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('context_data', sa.JSON(), nullable=True),
        sa.Column('status', sa.Text(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column('user_response', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('responded_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['workflow_executions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name='hitl_approvals_status_check')
    )
    op.create_index('idx_hitl_approvals_execution', 'hitl_approvals', ['execution_id'])
    op.create_index('idx_hitl_approvals_status', 'hitl_approvals', ['status'])
    op.create_index('idx_hitl_approvals_user', 'hitl_approvals', ['user_id'])

    # RLS Policies
    # Enable RLS on all tables
    op.execute("ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE workflow_executions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE conversation_sessions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE messages ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE hitl_approvals ENABLE ROW LEVEL SECURITY;")

    # Create RLS policies
    op.execute("""
        CREATE POLICY tenant_isolation_workflows ON workflows
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)

    op.execute("""
        CREATE POLICY tenant_isolation_workflow_executions ON workflow_executions
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)

    op.execute("""
        CREATE POLICY tenant_isolation_conversation_sessions ON conversation_sessions
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)

    op.execute("""
        CREATE POLICY tenant_isolation_messages ON messages
        USING (
            session_id IN (
                SELECT id FROM conversation_sessions
                WHERE tenant_id::text = current_setting('app.current_tenant', true)
            )
        );
    """)

    op.execute("""
        CREATE POLICY tenant_isolation_hitl_approvals ON hitl_approvals
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)


def downgrade() -> None:
    """Downgrade schema - Remove LangGraph v0.4 tables."""

    # Drop RLS policies first
    op.execute("DROP POLICY IF EXISTS tenant_isolation_hitl_approvals ON hitl_approvals;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_messages ON messages;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_conversation_sessions ON conversation_sessions;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_workflow_executions ON workflow_executions;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_workflows ON workflows;")

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_index('idx_hitl_approvals_user', 'hitl_approvals')
    op.drop_index('idx_hitl_approvals_status', 'hitl_approvals')
    op.drop_index('idx_hitl_approvals_execution', 'hitl_approvals')
    op.drop_table('hitl_approvals')

    op.drop_index('idx_messages_created', 'messages')
    op.drop_index('idx_messages_session', 'messages')
    op.drop_table('messages')

    op.drop_index('idx_conversation_sessions_thread', 'conversation_sessions')
    op.drop_index('idx_conversation_sessions_user', 'conversation_sessions')
    op.drop_index('idx_conversation_sessions_tenant', 'conversation_sessions')
    op.drop_table('conversation_sessions')

    op.drop_index('idx_workflow_executions_status', 'workflow_executions')
    op.drop_index('idx_workflow_executions_thread', 'workflow_executions')
    op.drop_index('idx_workflow_executions_tenant', 'workflow_executions')
    op.drop_table('workflow_executions')

    op.drop_index('idx_workflows_active', 'workflows')
    op.drop_index('idx_workflows_tenant', 'workflows')
    op.drop_table('workflows')
