"""
Workflow API endpoints for LangOrch v0.4

Provides REST API for workflow execution, streaming, and session management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List
import json
import structlog

from app.models.user import User
from app.api.dependencies import get_current_active_user
from app.services.workflow_service import WorkflowExecutionService
from app.schemas.workflow import (
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
    WorkflowResumeRequest
)
from app.schemas.conversation import (
    ConversationSessionCreate,
    ConversationSessionResponse,
    MessageCreate,
    MessageResponse
)

logger = structlog.get_logger()
router = APIRouter(tags=["Workflows"])


@router.post("/execute", response_model=WorkflowExecuteResponse)
async def execute_workflow(
    request: WorkflowExecuteRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Execute workflow to completion

    **v0.4.1+ Recommended**: Use unified workflow with automatic routing.
    If workflow_config is provided, it uses the old method (backward compatible).
    If not provided, uses the new unified workflow.

    This endpoint runs the workflow synchronously and returns the complete result.
    For streaming responses, use POST /workflows/execute/stream instead.

    Args:
        request: Workflow execution request
        current_user: Authenticated user

    Returns:
        Execution result with session_id, status, routing metadata, and output
    """
    service = WorkflowExecutionService(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )

    try:
        # Backward compatibility: Check if workflow_config is provided
        if request.workflow_config:
            # OLD WAY: Use provided workflow config (v0.4.0 backward compat)
            logger.warning(
                "workflow_config_deprecated",
                tenant_id=str(current_user.tenant_id),
                message="workflow_config parameter is deprecated. Use unified workflow (v0.4.1+) for automatic routing."
            )
            result = await service.execute_workflow(
                workflow_config=request.workflow_config,
                user_input=request.user_input,
                session_id=request.session_id,
                workflow_id=request.workflow_id
            )
        else:
            # NEW WAY: Use unified workflow (v0.4.1+)
            result = await service.execute_unified_workflow(
                user_input=request.user_input,
                session_id=request.session_id or str(__import__('uuid').uuid4()),
                workflow_id=request.workflow_id
            )

        return result

    except Exception as e:
        logger.error(
            "workflow_execution_endpoint_error",
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {str(e)}"
        )


from fastapi import Query

async def get_user_from_token_query(token: str = Query(None)) -> User:
    """
    Get user from token query parameter (for EventSource compatibility)
    EventSource cannot send custom headers, so we accept token as query param
    """
    import jwt
    from app.core.config import settings

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required"
        )

    try:
        # Decode JWT token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        # Get user from database
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )

            return user

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )


@router.get("/execute/stream")
async def stream_workflow_get(
    user_input: str,
    workflow_config: str = None,
    session_id: str = None,
    workflow_id: str = None,
    current_user: User = Depends(get_user_from_token_query)
):
    """
    Stream workflow execution via GET (for EventSource compatibility)

    **v0.4.1+ Recommended**: Use unified workflow with automatic routing.
    If workflow_config is provided, it uses the old method (backward compatible).
    If not provided, uses the new unified workflow.

    Query parameters:
        user_input: User input text
        workflow_config: Optional JSON string of workflow configuration (deprecated in v0.4.1+)
        session_id: Optional conversation session ID
        workflow_id: Optional workflow template ID
    """
    service = WorkflowExecutionService(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )

    async def event_generator():
        """Generate Server-Sent Events"""
        try:
            # Send start event
            yield f"event: start\ndata: {json.dumps({'status': 'started'})}\n\n"

            # Backward compatibility: Check if workflow_config is provided
            if workflow_config:
                # OLD WAY: Parse and use provided workflow config (v0.4.0 backward compat)
                import json as json_lib

                try:
                    config = json_lib.loads(workflow_config)
                except json_lib.JSONDecodeError as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid workflow_config JSON: {str(e)}"
                    )

                logger.warning(
                    "workflow_config_deprecated_stream",
                    tenant_id=str(current_user.tenant_id),
                    message="workflow_config parameter is deprecated. Use unified workflow (v0.4.1+) for automatic routing."
                )

                async for event in service.stream_workflow(
                    workflow_config=config,
                    user_input=user_input,
                    session_id=session_id,
                    workflow_id=workflow_id
                ):
                    yield f"event: update\ndata: {json.dumps(event)}\n\n"
            else:
                # NEW WAY: Use unified workflow (v0.4.1+)
                async for event in service.stream_unified_workflow(
                    user_input=user_input,
                    session_id=session_id or str(__import__('uuid').uuid4()),
                    workflow_id=workflow_id
                ):
                    yield f"event: update\ndata: {json.dumps(event)}\n\n"

            # Send done event
            yield f"event: done\ndata: {json.dumps({'status': 'completed'})}\n\n"

        except Exception as e:
            logger.error(
                "workflow_streaming_error",
                tenant_id=str(current_user.tenant_id),
                error=str(e)
            )
            # Send error event
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.post("/execute/stream")
async def stream_workflow_post(
    request: WorkflowExecuteRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Stream workflow execution via POST (alternative to GET)

    **v0.4.1+ Recommended**: Use unified workflow with automatic routing.
    If workflow_config is provided, it uses the old method (backward compatible).
    If not provided, uses the new unified workflow.

    This endpoint streams workflow events as they happen, enabling
    real-time UI updates and progressive response display.

    Event types:
    - start: Workflow started
    - update: State update from a node
    - done: Workflow completed
    - error: Workflow failed

    Args:
        request: Workflow execution request
        current_user: Authenticated user

    Returns:
        SSE stream of workflow events
    """
    service = WorkflowExecutionService(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )

    async def event_generator():
        """Generate Server-Sent Events"""
        try:
            # Send start event
            yield f"event: start\ndata: {json.dumps({'status': 'started'})}\n\n"

            # Backward compatibility: Check if workflow_config is provided
            if request.workflow_config:
                # OLD WAY: Use provided workflow config (v0.4.0 backward compat)
                logger.warning(
                    "workflow_config_deprecated_stream",
                    tenant_id=str(current_user.tenant_id),
                    message="workflow_config parameter is deprecated. Use unified workflow (v0.4.1+) for automatic routing."
                )

                async for event in service.stream_workflow(
                    workflow_config=request.workflow_config,
                    user_input=request.user_input,
                    session_id=request.session_id,
                    workflow_id=request.workflow_id
                ):
                    yield f"event: update\ndata: {json.dumps(event)}\n\n"
            else:
                # NEW WAY: Use unified workflow (v0.4.1+)
                async for event in service.stream_unified_workflow(
                    user_input=request.user_input,
                    session_id=request.session_id or str(__import__('uuid').uuid4()),
                    workflow_id=request.workflow_id
                ):
                    yield f"event: update\ndata: {json.dumps(event)}\n\n"

            # Send done event
            yield f"event: done\ndata: {json.dumps({'status': 'completed'})}\n\n"

        except Exception as e:
            logger.error(
                "workflow_streaming_error",
                tenant_id=str(current_user.tenant_id),
                error=str(e)
            )
            # Send error event
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.post("/resume")
async def resume_workflow(
    request: WorkflowResumeRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Resume interrupted workflow (HITL)

    Used when a workflow is paused at a Human-in-the-Loop node
    waiting for user approval or input.

    Args:
        request: Resume request with session_id and user_response
        current_user: Authenticated user

    Returns:
        Resume result
    """
    service = WorkflowExecutionService(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )

    try:
        result = await service.resume_workflow(
            session_id=request.session_id,
            user_response=request.user_response
        )

        return result

    except Exception as e:
        logger.error(
            "workflow_resume_error",
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume workflow: {str(e)}"
        )


# ========== Session Management ==========

@router.post("/sessions", response_model=ConversationSessionResponse)
async def create_session(
    request: ConversationSessionCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create new conversation session"""
    service = WorkflowExecutionService(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )

    session = await service.create_session(
        workflow_id=request.workflow_id,
        title=request.title
    )

    return session


@router.get("/sessions", response_model=List[ConversationSessionResponse])
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user)
):
    """List user's conversation sessions"""
    service = WorkflowExecutionService(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )

    sessions = await service.list_sessions(limit=limit, offset=offset)

    return sessions


@router.get("/sessions/{session_id}", response_model=ConversationSessionResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get conversation session by ID"""
    from uuid import UUID

    service = WorkflowExecutionService(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )

    try:
        session = await service.get_session(UUID(session_id))
        return session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {str(e)}"
        )


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: str,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user)
):
    """Get messages for a session"""
    from uuid import UUID

    service = WorkflowExecutionService(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )

    try:
        messages = await service.get_messages(UUID(session_id), limit=limit)
        return messages
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve messages: {str(e)}"
        )


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def add_session_message(
    session_id: str,
    request: MessageCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Add message to session"""
    from uuid import UUID

    service = WorkflowExecutionService(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )

    try:
        message = await service.add_message(
            session_id=UUID(session_id),
            role=request.role,
            content=request.content
        )
        return message
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add message: {str(e)}"
        )
