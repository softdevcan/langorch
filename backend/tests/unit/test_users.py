"""
User endpoint tests
"""
import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_create_user_as_admin(
    client: AsyncClient,
    admin_auth_headers: dict,
    test_tenant: User,
):
    """Test creating user as admin"""
    response = await client.post(
        "/api/v1/users/",
        headers=admin_auth_headers,
        json={
            "email": "newuser@example.com",
            "password": "NewUser1234",
            "full_name": "New User",
            "role": "user",
            "tenant_id": str(test_tenant.id),
            "is_active": True,
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"


@pytest.mark.asyncio
async def test_create_user_unauthorized(client: AsyncClient, auth_headers: dict, test_tenant: User):
    """Test creating user as regular user (should fail)"""
    response = await client.post(
        "/api/v1/users/",
        headers=auth_headers,
        json={
            "email": "unauthorized@example.com",
            "password": "Test1234",
            "full_name": "Unauthorized",
            "role": "user",
            "tenant_id": str(test_tenant.id),
            "is_active": True,
        }
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_users(client: AsyncClient, auth_headers: dict, test_user: User):
    """Test listing users"""
    response = await client.get(
        "/api/v1/users/",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_user(client: AsyncClient, auth_headers: dict, test_user: User):
    """Test getting single user"""
    response = await client.get(
        f"/api/v1/users/{test_user.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient, admin_auth_headers: dict, test_user: User):
    """Test updating user"""
    response = await client.patch(
        f"/api/v1/users/{test_user.id}",
        headers=admin_auth_headers,
        json={
            "full_name": "Updated Name",
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient, admin_auth_headers: dict, test_user: User):
    """Test deleting user"""
    response = await client.delete(
        f"/api/v1/users/{test_user.id}",
        headers=admin_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_tenant_isolation(
    client: AsyncClient,
    auth_headers: dict,
    test_user: User,
    db_session,
):
    """Test that users can't access other tenants' users"""
    # Create another tenant and user
    from app.models.tenant import Tenant
    from app.core.security import security

    other_tenant = Tenant(
        name="Other Org",
        slug="other-org",
        is_active=True,
    )
    db_session.add(other_tenant)
    await db_session.commit()
    await db_session.refresh(other_tenant)

    other_user = User(
        email="other@example.com",
        hashed_password=security.hash_password("Other1234"),
        full_name="Other User",
        role="user",
        tenant_id=other_tenant.id,
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    # Try to access other tenant's user
    response = await client.get(
        f"/api/v1/users/{other_user.id}",
        headers=auth_headers,
    )

    assert response.status_code == 404  # Should not find user from different tenant
