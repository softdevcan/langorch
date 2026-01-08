"""
Database models
"""
from app.models.base import Base, BaseModel
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.models.llm_conversation import LLMConversation
from app.models.llm_message import LLMMessage
from app.models.llm_operation import LLMOperation

# v0.4 LangGraph models
from app.models.workflow import Workflow
from app.models.workflow_execution import WorkflowExecution
from app.models.conversation_session import ConversationSession
from app.models.message import Message
from app.models.hitl_approval import HITLApproval

__all__ = [
    "Base",
    "BaseModel",
    "Tenant",
    "User",
    "UserRole",
    "AuditLog",
    "Document",
    "DocumentStatus",
    "DocumentChunk",
    "LLMConversation",
    "LLMMessage",
    "LLMOperation",
    # v0.4 models
    "Workflow",
    "WorkflowExecution",
    "ConversationSession",
    "Message",
    "HITLApproval",
]
