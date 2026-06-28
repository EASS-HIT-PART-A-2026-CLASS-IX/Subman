"""
test_auth.py — JWT security tests for SubMan Pro.

Three scenarios that must all pass:
  1. No token        → 401
  2. Expired token   → 401
  3. Valid admin token → 200
"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.auth import create_access_token
from app.main import app, get_session


# ---------------------------------------------------------------------------
# Fixtures — same in-memory DB pattern as existing tests
# ---------------------------------------------------------------------------

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def override():
        return session

    app.dependency_overrides[get_session] = override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper — seed one subscription so DELETE has something to act on
# ---------------------------------------------------------------------------

def _seed(client: TestClient) -> str:
    name = "Auth Test Sub"
    client.post(
        "/subscriptions",
        json={
            "name": name,
            "price": 10.0,
            "currency": "ILS",
            "category": "other",
            "billing_cycle": "monthly",
            "status": "active",
            "purchase_date": "2026-06-01",
        },
    )
    return name


# ---------------------------------------------------------------------------
# Test 1 — no token → 401
# ---------------------------------------------------------------------------

def test_delete_requires_token(client: TestClient):
    """DELETE without any Authorization header must return 401."""
    name = _seed(client)
    response = client.delete(f"/subscriptions/{name}")
    assert response.status_code == 401, (
        f"Expected 401 without token, got {response.status_code}"
    )


# ---------------------------------------------------------------------------
# Test 2 — expired token → 401
# ---------------------------------------------------------------------------

def test_delete_expired_token_is_rejected(client: TestClient):
    """DELETE with a token that expired 1 second ago must return 401."""
    name = _seed(client)
    expired_token = create_access_token(
        {"sub": "admin", "role": "admin"},
        expires_delta=timedelta(seconds=-1),   # already expired
    )
    response = client.delete(
        f"/subscriptions/{name}",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401, (
        f"Expected 401 for expired token, got {response.status_code}"
    )
    assert "expired" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test 3 — viewer role → 403 (wrong scope)
# ---------------------------------------------------------------------------

def test_delete_viewer_role_is_forbidden(client: TestClient):
    """DELETE with a valid token but viewer role must return 403."""
    name = _seed(client)
    viewer_token = create_access_token({"sub": "viewer", "role": "viewer"})
    response = client.delete(
        f"/subscriptions/{name}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403, (
        f"Expected 403 for viewer role, got {response.status_code}"
    )


# ---------------------------------------------------------------------------
# Test 4 — valid admin token → 200
# ---------------------------------------------------------------------------

def test_delete_valid_admin_token_succeeds(client: TestClient):
    """DELETE with a valid admin token must return 200 and remove the record."""
    name = _seed(client)
    admin_token = create_access_token({"sub": "admin", "role": "admin"})
    response = client.delete(
        f"/subscriptions/{name}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, (
        f"Expected 200 for valid admin token, got {response.status_code}"
    )
    assert response.json()["message"] == "Deleted successfully"