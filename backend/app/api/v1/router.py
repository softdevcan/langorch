"""
API v1 router - combines all endpoint routers
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    tenants,
    documents,
    secrets,
    settings,
    llm_operations,
    workflows,  # v0.4
    hitl,       # v0.4
    sessions    # v0.4.1
)

# Create API v1 router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tenants.router)
api_router.include_router(documents.router)
api_router.include_router(secrets.router)
api_router.include_router(settings.router, prefix="/settings")  # Settings endpoints
api_router.include_router(llm_operations.router)  # LLM operations endpoints

# v0.4 - LangGraph workflow orchestration
api_router.include_router(workflows.router, prefix="/workflows")  # Workflow execution & sessions
api_router.include_router(hitl.router, prefix="/hitl")  # Human-in-the-Loop approvals

# v0.4.1 - Session enhancement with document management
api_router.include_router(sessions.router, prefix="/sessions")  # Session document management
