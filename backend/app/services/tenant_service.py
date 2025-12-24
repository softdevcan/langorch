"""
Tenant service - CRUD operations for tenants
"""
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
import structlog

from app.core.exceptions import (
    NotFoundException,
    ConflictException,
)
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate

logger = structlog.get_logger()


class TenantService:
    """Tenant service for CRUD operations"""

    @staticmethod
    async def create_tenant(
        db: AsyncSession,
        tenant_data: TenantCreate,
    ) -> Tenant:
        """
        Create a new tenant

        Args:
            db: Database session
            tenant_data: Tenant creation data

        Returns:
            Created tenant

        Raises:
            ConflictException: If slug or domain already exists
        """
        # Check if slug already exists
        result = await db.execute(
            select(Tenant).where(Tenant.slug == tenant_data.slug)
        )
        existing_tenant = result.scalar_one_or_none()

        if existing_tenant:
            raise ConflictException(
                "Tenant already exists",
                detail=f"Slug '{tenant_data.slug}' is already taken"
            )

        # Check if domain already exists (if provided)
        if tenant_data.domain:
            result = await db.execute(
                select(Tenant).where(Tenant.domain == tenant_data.domain)
            )
            existing_domain = result.scalar_one_or_none()

            if existing_domain:
                raise ConflictException(
                    "Domain already exists",
                    detail=f"Domain '{tenant_data.domain}' is already registered"
                )

        # Create tenant
        tenant = Tenant(
            name=tenant_data.name,
            slug=tenant_data.slug,
            domain=tenant_data.domain,
            is_active=tenant_data.is_active,
            settings=tenant_data.settings,
        )

        try:
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)

            logger.info(
                "tenant_created",
                tenant_id=str(tenant.id),
                name=tenant.name,
                slug=tenant.slug,
            )

            return tenant

        except IntegrityError as e:
            await db.rollback()
            logger.error("tenant_creation_failed", error=str(e))
            raise ConflictException(
                "Tenant creation failed",
                detail="Database constraint violation"
            )

    @staticmethod
    async def get_tenant(
        db: AsyncSession,
        tenant_id: UUID,
    ) -> Tenant:
        """
        Get tenant by ID

        Args:
            db: Database session
            tenant_id: Tenant ID

        Returns:
            Tenant

        Raises:
            NotFoundException: If tenant not found
        """
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise NotFoundException(
                "Tenant not found",
                detail=f"Tenant with ID {tenant_id} not found"
            )

        return tenant

    @staticmethod
    async def get_tenant_by_slug(
        db: AsyncSession,
        slug: str,
    ) -> Tenant:
        """
        Get tenant by slug

        Args:
            db: Database session
            slug: Tenant slug

        Returns:
            Tenant

        Raises:
            NotFoundException: If tenant not found
        """
        result = await db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise NotFoundException(
                "Tenant not found",
                detail=f"Tenant with slug '{slug}' not found"
            )

        return tenant

    @staticmethod
    async def list_tenants(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False,
    ) -> tuple[List[Tenant], int]:
        """
        List tenants with pagination

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: Only return active tenants

        Returns:
            Tuple of (tenants list, total count)
        """
        query = select(Tenant)

        if active_only:
            query = query.where(Tenant.is_active == True)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(Tenant.created_at.desc())
        result = await db.execute(query)
        tenants = result.scalars().all()

        logger.info(
            "tenants_listed",
            total=total,
            returned=len(tenants),
            active_only=active_only,
        )

        return list(tenants), total

    @staticmethod
    async def update_tenant(
        db: AsyncSession,
        tenant_id: UUID,
        tenant_data: TenantUpdate,
    ) -> Tenant:
        """
        Update tenant

        Args:
            db: Database session
            tenant_id: Tenant ID
            tenant_data: Tenant update data

        Returns:
            Updated tenant

        Raises:
            NotFoundException: If tenant not found
            ConflictException: If domain already exists
        """
        # Get existing tenant
        tenant = await TenantService.get_tenant(db, tenant_id)

        # Check domain uniqueness if updating domain
        if tenant_data.domain and tenant_data.domain != tenant.domain:
            result = await db.execute(
                select(Tenant).where(Tenant.domain == tenant_data.domain)
            )
            existing_domain = result.scalar_one_or_none()
            if existing_domain:
                raise ConflictException(
                    "Domain already exists",
                    detail=f"Domain '{tenant_data.domain}' is already registered"
                )

        # Update fields
        update_data = tenant_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(tenant, field, value)

        try:
            await db.commit()
            await db.refresh(tenant)

            logger.info(
                "tenant_updated",
                tenant_id=str(tenant.id),
                updated_fields=list(update_data.keys()),
            )

            return tenant

        except IntegrityError as e:
            await db.rollback()
            logger.error("tenant_update_failed", error=str(e))
            raise ConflictException(
                "Tenant update failed",
                detail="Database constraint violation"
            )

    @staticmethod
    async def delete_tenant(
        db: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        """
        Delete tenant (cascades to users, documents, etc.)

        Args:
            db: Database session
            tenant_id: Tenant ID

        Raises:
            NotFoundException: If tenant not found
        """
        tenant = await TenantService.get_tenant(db, tenant_id)

        await db.delete(tenant)
        await db.commit()

        logger.info(
            "tenant_deleted",
            tenant_id=str(tenant_id),
            name=tenant.name,
        )


# Create singleton instance
tenant_service = TenantService()
