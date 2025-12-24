"""
Pytest configuration and fixtures
"""
import asyncio
from typing import AsyncGenerator, Generator
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient

from app.main import app
from app.core.config import settings
from app.core.database import get_db
from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.core.security import security


# Test database URL (use in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_engine():
    """Create test database engine"""
    from app.models import Tenant, User, AuditLog  # Import all models

    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client"""
    from httpx import ASGITransport

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create test tenant"""
    tenant = Tenant(
        name="Test Organization",
        slug="test-org",
        domain="test.example.com",
        is_active=True,
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture(scope="function")
async def test_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create test user"""
    user = User(
        email="test@example.com",
        hashed_password=security.hash_password("Test1234"),
        full_name="Test User",
        role=UserRole.USER,
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def test_admin_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create test admin user"""
    admin = User(
        email="admin@example.com",
        hashed_password=security.hash_password("Admin1234"),
        full_name="Admin User",
        role=UserRole.TENANT_ADMIN,
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture(scope="function")
async def test_super_admin(db_session: AsyncSession) -> User:
    """Create test super admin user"""
    super_admin = User(
        email="superadmin@example.com",
        hashed_password=security.hash_password("Super1234"),
        full_name="Super Admin",
        role=UserRole.SUPER_ADMIN,
        tenant_id=None,
        is_active=True,
    )
    db_session.add(super_admin)
    await db_session.commit()
    await db_session.refresh(super_admin)
    return super_admin


@pytest.fixture(scope="function")
async def auth_headers(test_user: User) -> dict:
    """Get authentication headers for test user"""
    token = security.create_access_token(
        user_id=test_user.id,
        email=test_user.email,
        role=test_user.role,
        tenant_id=test_user.tenant_id,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
async def admin_auth_headers(test_admin_user: User) -> dict:
    """Get authentication headers for admin user"""
    token = security.create_access_token(
        user_id=test_admin_user.id,
        email=test_admin_user.email,
        role=test_admin_user.role,
        tenant_id=test_admin_user.tenant_id,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
async def super_admin_auth_headers(test_super_admin: User) -> dict:
    """Get authentication headers for super admin"""
    token = security.create_access_token(
        user_id=test_super_admin.id,
        email=test_super_admin.email,
        role=test_super_admin.role,
        tenant_id=test_super_admin.tenant_id,
    )
    return {"Authorization": f"Bearer {token}"}
