"""
Seed script to create test data for development and testing
"""
import asyncio
import sys
import json
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.database import AsyncSessionLocal, engine
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.core.security import SecurityManager
import structlog

logger = structlog.get_logger()


async def create_test_data():
    """Create test tenant and users"""
    async with AsyncSessionLocal() as session:
        try:
            # Check if test tenant already exists
            from sqlalchemy import select
            result = await session.execute(
                select(Tenant).where(Tenant.slug == "test-tenant")
            )
            existing_tenant = result.scalar_one_or_none()

            if existing_tenant:
                logger.info("Test tenant already exists", tenant_id=existing_tenant.id)
                tenant = existing_tenant
            else:
                # Create test tenant
                tenant = Tenant(
                    name="Test Tenant",
                    slug="test-tenant",
                    settings=json.dumps({"api_enabled": True}),
                    is_active=True
                )
                session.add(tenant)
                await session.flush()
                logger.info("Created test tenant", tenant_id=tenant.id)

            # Check if test admin already exists
            result = await session.execute(
                select(User).where(User.email == "admin@test.com")
            )
            existing_admin = result.scalar_one_or_none()

            if not existing_admin:
                # Create tenant admin user
                admin_user = User(
                    email="admin@test.com",
                    full_name="Admin User",
                    hashed_password=SecurityManager.hash_password("admin123"),
                    role=UserRole.TENANT_ADMIN,
                    tenant_id=tenant.id,
                    is_active=True
                )
                session.add(admin_user)
                logger.info("Created admin user", email="admin@test.com")
            else:
                logger.info("Admin user already exists", email="admin@test.com")

            # Check if test user already exists
            result = await session.execute(
                select(User).where(User.email == "user@test.com")
            )
            existing_user = result.scalar_one_or_none()

            if not existing_user:
                # Create regular user
                regular_user = User(
                    email="user@test.com",
                    full_name="Regular User",
                    hashed_password=SecurityManager.hash_password("user123"),
                    role=UserRole.USER,
                    tenant_id=tenant.id,
                    is_active=True
                )
                session.add(regular_user)
                logger.info("Created regular user", email="user@test.com")
            else:
                logger.info("Regular user already exists", email="user@test.com")

            await session.commit()

            logger.info("✅ Test data seeding completed successfully!")
            logger.info("Login credentials:")
            logger.info("  Admin: admin@test.com / admin123")
            logger.info("  User:  user@test.com / user123")

        except Exception as e:
            await session.rollback()
            logger.error("Failed to seed test data", error=str(e))
            raise


async def main():
    """Main function"""
    logger.info("Starting test data seeding...")
    await create_test_data()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
