"""
Workflow schemas for LangGraph v0.4
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


# ============ Base Schemas ============

class WorkflowConfigNode(BaseModel):
    """Workflow node configuration"""
    id: str = Field(..., description="Unique node identifier")
    type: str = Field(..., description="Node type (llm, retriever, tool, human_in_loop)")
    config: Dict[str, Any] = Field(default_factory=dict, description="Node-specific configuration")


class WorkflowConfigEdge(BaseModel):
    """Workflow edge configuration"""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    condition: Optional[str] = Field(None, description="Conditional routing logic")
    mapping: Optional[Dict[str, str]] = Field(None, description="State field mappings")


class WorkflowConfig(BaseModel):
    """Complete workflow configuration"""
    name: str = Field(..., description="Workflow name")
    version: str = Field(default="1.0", description="Workflow version")
    description: Optional[str] = Field(None, description="Workflow description")
    state_schema: Optional[Dict[str, Any]] = Field(None, description="State schema definition")
    nodes: List[WorkflowConfigNode] = Field(..., description="Workflow nodes")
    edges: List[WorkflowConfigEdge] = Field(..., description="Workflow edges")


# ============ Workflow CRUD Schemas ============

class WorkflowBase(BaseModel):
    """Base workflow schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    workflow_config: WorkflowConfig
    is_active: bool = True


class WorkflowCreate(WorkflowBase):
    """Schema for creating a workflow"""
    pass


class WorkflowUpdate(BaseModel):
    """Schema for updating a workflow"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    workflow_config: Optional[WorkflowConfig] = None
    is_active: Optional[bool] = None


class WorkflowResponse(WorkflowBase):
    """Schema for workflow response"""
    id: UUID
    tenant_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Workflow Execution Schemas ============

class WorkflowExecuteRequest(BaseModel):
    """Request to execute a workflow"""
    workflow_id: Optional[UUID] = Field(None, description="Workflow ID (if using saved workflow)")
    workflow_config: Optional[WorkflowConfig] = Field(None, description="Inline workflow config")
    user_input: str = Field(..., description="User input/query")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")

    def model_post_init(self, __context):
        """Validate that either workflow_id or workflow_config is provided"""
        if not self.workflow_id and not self.workflow_config:
            raise ValueError("Either workflow_id or workflow_config must be provided")


class WorkflowExecuteResponse(BaseModel):
    """Response from workflow execution"""
    session_id: str
    status: str  # running, completed, failed, interrupted
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class WorkflowResumeRequest(BaseModel):
    """Request to resume interrupted workflow (HITL)"""
    session_id: str = Field(..., description="Session ID to resume")
    user_input: Dict[str, Any] = Field(..., description="User's response to HITL prompt")


# ============ Workflow Execution Status ============

class WorkflowExecutionResponse(BaseModel):
    """Workflow execution status"""
    id: UUID
    tenant_id: UUID
    user_id: UUID
    workflow_id: Optional[UUID]
    thread_id: str
    status: str
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
