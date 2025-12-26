"""v02_add_documents_and_chunks_with_rls

Revision ID: c7094c3584af
Revises: bf0ada04bd0a
Create Date: 2025-12-26 22:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'c7094c3584af'
down_revision: Union[str, Sequence[str], None] = 'bf0ada04bd0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add documents and document_chunks tables with RLS."""

    # Enable pgvector extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Create documents table
    op.create_table(
        'documents',
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False, comment='Tenant ID for multi-tenant isolation'),
        sa.Column('user_id', UUID(as_uuid=True), nullable=True, comment='User who uploaded the document'),
        sa.Column('filename', sa.String(length=500), nullable=False, comment='Original filename'),
        sa.Column('file_path', sa.String(length=1000), nullable=False, comment='Storage path (S3, local filesystem, etc.)'),
        sa.Column('file_size', sa.Integer(), nullable=False, comment='File size in bytes'),
        sa.Column('file_type', sa.String(length=100), nullable=False, comment="MIME type (e.g., 'application/pdf', 'text/plain')"),
        sa.Column('status', sa.Enum('UPLOADING', 'PROCESSING', 'COMPLETED', 'FAILED', 'DELETED', name='documentstatus', native_enum=False), nullable=False, comment='Document processing status'),
        sa.Column('content', sa.Text(), nullable=True, comment='Extracted text content (for full-text search)'),
        sa.Column('embedding', sa.TEXT(), nullable=True, comment='Document-level embedding vector (1536 dimensions)'),  # Will use vector type
        sa.Column('metadata', JSONB(), nullable=True, comment='Additional metadata (author, title, tags, etc.)'),
        sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0', comment='Number of chunks created from this document'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='Error message if processing failed'),
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for documents
    op.create_index(op.f('ix_documents_id'), 'documents', ['id'], unique=False)
    op.create_index(op.f('ix_documents_tenant_id'), 'documents', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_documents_user_id'), 'documents', ['user_id'], unique=False)
    op.create_index(op.f('ix_documents_status'), 'documents', ['status'], unique=False)
    op.create_index('ix_documents_tenant_status', 'documents', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_documents_user_created', 'documents', ['user_id', 'created_at'], unique=False)

    # Alter embedding column to use vector type
    op.execute("ALTER TABLE documents ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536);")

    # Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('document_id', UUID(as_uuid=True), nullable=False, comment='Parent document ID'),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False, comment='Tenant ID (denormalized from document)'),
        sa.Column('chunk_index', sa.Integer(), nullable=False, comment='Sequential index within the document (0-based)'),
        sa.Column('content', sa.Text(), nullable=False, comment='Chunk text content'),
        sa.Column('token_count', sa.Integer(), nullable=False, comment='Number of tokens in this chunk'),
        sa.Column('embedding', sa.TEXT(), nullable=False, comment='Chunk embedding vector (1536 dimensions)'),  # Will use vector type
        sa.Column('metadata', JSONB(), nullable=True, comment='Chunk-specific metadata (page_number, section, etc.)'),
        sa.Column('start_char', sa.Integer(), nullable=True, comment='Start character position in original document'),
        sa.Column('end_char', sa.Integer(), nullable=True, comment='End character position in original document'),
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for document_chunks
    op.create_index(op.f('ix_document_chunks_id'), 'document_chunks', ['id'], unique=False)
    op.create_index(op.f('ix_document_chunks_document_id'), 'document_chunks', ['document_id'], unique=False)
    op.create_index(op.f('ix_document_chunks_tenant_id'), 'document_chunks', ['tenant_id'], unique=False)
    op.create_index('ix_document_chunks_document_index', 'document_chunks', ['document_id', 'chunk_index'], unique=False)
    op.create_index('ix_document_chunks_tenant_created', 'document_chunks', ['tenant_id', 'created_at'], unique=False)
    op.create_index('ix_document_chunks_tenant_document', 'document_chunks', ['tenant_id', 'document_id'], unique=False)

    # Alter embedding column to use vector type
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536);")

    # Create vector indexes (IVFFlat) for similarity search
    # IVFFlat parameters: lists = sqrt(total_rows) is a good starting point
    # For small datasets, we'll use 100 lists
    op.execute("""
        CREATE INDEX ix_documents_embedding_ivfflat
        ON documents
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)

    op.execute("""
        CREATE INDEX ix_document_chunks_embedding_ivfflat
        ON document_chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)

    # Enable Row Level Security (RLS) on documents
    op.execute("ALTER TABLE documents ENABLE ROW LEVEL SECURITY;")

    # Create RLS policy for documents - Users can only see documents in their tenant
    op.execute("""
        CREATE POLICY documents_tenant_isolation ON documents
        USING (tenant_id::text = current_setting('app.current_tenant', TRUE))
        WITH CHECK (tenant_id::text = current_setting('app.current_tenant', TRUE));
    """)

    # Enable Row Level Security (RLS) on document_chunks
    op.execute("ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;")

    # Create RLS policy for document_chunks - Users can only see chunks in their tenant
    op.execute("""
        CREATE POLICY document_chunks_tenant_isolation ON document_chunks
        USING (tenant_id::text = current_setting('app.current_tenant', TRUE))
        WITH CHECK (tenant_id::text = current_setting('app.current_tenant', TRUE));
    """)

    # Enable RLS on users table (for consistency)
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")

    # Create RLS policy for users - Users can only see users in their tenant (or super_admin can see all)
    op.execute("""
        CREATE POLICY users_tenant_isolation ON users
        USING (
            tenant_id::text = current_setting('app.current_tenant', TRUE)
            OR current_setting('app.current_tenant', TRUE) = ''
            OR current_setting('app.current_tenant', TRUE) IS NULL
        )
        WITH CHECK (
            tenant_id::text = current_setting('app.current_tenant', TRUE)
            OR current_setting('app.current_tenant', TRUE) = ''
            OR current_setting('app.current_tenant', TRUE) IS NULL
        );
    """)


def downgrade() -> None:
    """Downgrade schema - Remove documents and document_chunks tables with RLS."""

    # Disable RLS and drop policies for users
    op.execute("DROP POLICY IF EXISTS users_tenant_isolation ON users;")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY;")

    # Disable RLS and drop policies for document_chunks
    op.execute("DROP POLICY IF EXISTS document_chunks_tenant_isolation ON document_chunks;")
    op.execute("ALTER TABLE document_chunks DISABLE ROW LEVEL SECURITY;")

    # Disable RLS and drop policies for documents
    op.execute("DROP POLICY IF EXISTS documents_tenant_isolation ON documents;")
    op.execute("ALTER TABLE documents DISABLE ROW LEVEL SECURITY;")

    # Drop vector indexes
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_ivfflat;")
    op.execute("DROP INDEX IF EXISTS ix_documents_embedding_ivfflat;")

    # Drop document_chunks indexes
    op.drop_index('ix_document_chunks_tenant_document', table_name='document_chunks')
    op.drop_index('ix_document_chunks_tenant_created', table_name='document_chunks')
    op.drop_index('ix_document_chunks_document_index', table_name='document_chunks')
    op.drop_index(op.f('ix_document_chunks_tenant_id'), table_name='document_chunks')
    op.drop_index(op.f('ix_document_chunks_document_id'), table_name='document_chunks')
    op.drop_index(op.f('ix_document_chunks_id'), table_name='document_chunks')

    # Drop document_chunks table
    op.drop_table('document_chunks')

    # Drop documents indexes
    op.drop_index('ix_documents_user_created', table_name='documents')
    op.drop_index('ix_documents_tenant_status', table_name='documents')
    op.drop_index(op.f('ix_documents_status'), table_name='documents')
    op.drop_index(op.f('ix_documents_user_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_tenant_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_id'), table_name='documents')

    # Drop documents table
    op.drop_table('documents')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS documentstatus;")
