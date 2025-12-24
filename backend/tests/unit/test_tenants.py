"""
Tenant endpoint tests
"""
import pytest
from httpx import AsyncClient

from app.models.user import User
from app.models.tenant import Tenant


@pytest.mark.asyncio
async def test_create_tenant_as_super_admin(
    client: AsyncClient,
    super_admin_auth_headers: dict,
):
    """Test creating tenant as super admin"""
    response = await client.post(
        "/api/v1/tenants/",
        headers=super_admin_auth_headers,
        json={
            "name": "New Organization",
            "slug": "new-org",
            "domain": "new.example.com",
            "is_active": True,
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Organization"
    assert data["slug"] == "new-org"


@pytest.mark.asyncio
async def test_create_tenant_unauthorized(client: AsyncClient, admin_auth_headers: dict):
    """Test creating tenant as tenant admin (should fail)"""
    response = await client.post(
        "/api/v1/tenants/",
        headers=admin_auth_headers,
        json={
            "name": "Unauthorized Org",
            "slug": "unauthorized-org",
            "is_active": True,
        }
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_tenants(client: AsyncClient, super_admin_auth_headers: dict, test_tenant: Tenant):
    """Test listing tenants"""
    response = await client.get(
        "/api/v1/tenants/",
        headers=super_admin_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_tenant(
    client: AsyncClient,
    admin_auth_headers: dict,
    test_tenant: Tenant,
):
    """Test getting single tenant"""
    response = await client.get(
        f"/api/v1/tenants/{test_tenant.id}",
        headers=admin_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == test_tenant.name


@pytest.mark.asyncio
async def test_update_tenant(
    client: AsyncClient,
    super_admin_auth_headers: dict,
    test_tenant: Tenant,
):
    """Test updating tenant"""
    response = await client.patch(
        f"/api/v1/tenants/{test_tenant.id}",
        headers=super_admin_auth_headers,
        json={
            "name": "Updated Organization",
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Organization"


@pytest.mark.asyncio
async def test_delete_tenant(
    client: AsyncClient,
    super_admin_auth_headers: dict,
    db_session,
):
    """Test deleting tenant"""
    # Create a tenant to delete
    from app.models.tenant import Tenant

    tenant = Tenant(
        name="To Delete",
        slug="to-delete",
        is_active=True,
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    response = await client.delete(
        f"/api/v1/tenants/{tenant.id}",
        headers=super_admin_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_tenant_admin_cannot_access_other_tenant(
    client: AsyncClient,
    admin_auth_headers: dict,
    db_session,
):
    """Test that tenant admin can't access other tenants"""
    # Create another tenant
    from app.models.tenant import Tenant

    other_tenant = Tenant(
        name="Other Organization",
        slug="other-org-test",
        is_active=True,
    )
    db_session.add(other_tenant)
    await db_session.commit()
    await db_session.refresh(other_tenant)

    # Try to access other tenant
    response = await client.get(
        f"/api/v1/tenants/{other_tenant.id}",
        headers=admin_auth_headers,
    )

    assert response.status_code == 404  # Should not have access
