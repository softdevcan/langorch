"""
Tenant management endpoints
"""
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
    http_404_not_found,
    http_409_conflict,
)
from app.api.dependencies import require_role
from app.models.user import User, UserRole
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse, TenantListResponse
from app.schemas import MessageResponse
from app.services.tenant_service import tenant_service

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.post(
    "/",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create tenant",
    description="Create a new tenant (super admin only)",
)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
):
    """
    Create a new tenant

    - **name**: Organization name
    - **slug**: URL-friendly identifier (must be unique)
    - **domain**: Custom domain (optional, must be unique)
    - **is_active**: Tenant active status
    - **settings**: Tenant-specific settings JSON (optional)

    Requires: SUPER_ADMIN role
    """
    try:
        tenant = await tenant_service.create_tenant(db, tenant_data)
        logger.info("tenant_created_via_api", tenant_id=str(tenant.id), created_by=str(current_user.id))
        return tenant
    except ConflictException as e:
        raise http_409_conflict(detail=e.detail or e.message)


@router.get(
    "/",
    response_model=TenantListResponse,
    status_code=status.HTTP_200_OK,
    summary="List tenants",
    description="List all tenants with pagination (super admin only)",
)
async def list_tenants(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    active_only: bool = Query(False, description="Only return active tenants"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
):
    """
    List all tenants with pagination

    - **skip**: Pagination offset
    - **limit**: Maximum results per page
    - **active_only**: Filter for active tenants only

    Requires: SUPER_ADMIN role
    """
    tenants, total = await tenant_service.list_tenants(db, skip, limit, active_only)

    return TenantListResponse(
        items=tenants,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
    )


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    status_code=status.HTTP_200_OK,
    summary="Get tenant",
    description="Get tenant by ID",
)
async def get_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN)),
):
    """
    Get tenant by ID

    Requires: SUPER_ADMIN or TENANT_ADMIN role
    """
    try:
        # Tenant admins can only view their own tenant
        if current_user.role == UserRole.TENANT_ADMIN:
            if current_user.tenant_id != tenant_id:
                raise NotFoundException(
                    "Tenant not found",
                    detail="Access denied to this tenant"
                )

        tenant = await tenant_service.get_tenant(db, tenant_id)
        return tenant
    except NotFoundException as e:
        raise http_404_not_found(detail=e.detail or e.message)


@router.patch(
    "/{tenant_id}",
    response_model=TenantResponse,
    status_code=status.HTTP_200_OK,
    summary="Update tenant",
    description="Update tenant by ID",
)
async def update_tenant(
    tenant_id: UUID,
    tenant_data: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN)),
):
    """
    Update tenant

    - **name**: New organization name (optional)
    - **domain**: New custom domain (optional)
    - **is_active**: New active status (optional)
    - **settings**: New settings JSON (optional)

    Requires: SUPER_ADMIN or TENANT_ADMIN role
    """
    try:
        # Tenant admins can only update their own tenant
        if current_user.role == UserRole.TENANT_ADMIN:
            if current_user.tenant_id != tenant_id:
                raise NotFoundException(
                    "Tenant not found",
                    detail="Access denied to this tenant"
                )

        tenant = await tenant_service.update_tenant(db, tenant_id, tenant_data)
        logger.info("tenant_updated_via_api", tenant_id=str(tenant_id), updated_by=str(current_user.id))
        return tenant
    except NotFoundException as e:
        raise http_404_not_found(detail=e.detail or e.message)
    except ConflictException as e:
        raise http_409_conflict(detail=e.detail or e.message)


@router.delete(
    "/{tenant_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete tenant",
    description="Delete tenant by ID (super admin only)",
)
async def delete_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
):
    """
    Delete tenant

    Warning: This will cascade delete all users, documents, etc.

    Requires: SUPER_ADMIN role
    """
    try:
        await tenant_service.delete_tenant(db, tenant_id)
        logger.info("tenant_deleted_via_api", tenant_id=str(tenant_id), deleted_by=str(current_user.id))
        return MessageResponse(message="Tenant deleted successfully")
    except NotFoundException as e:
        raise http_404_not_found(detail=e.detail or e.message)
