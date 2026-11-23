"""Shared pytest fixtures for the FastAPI backend."""

import os
from contextlib import contextmanager

# Make environment lookups inside services (e.g. rate limiting) see testing mode.
os.environ["APP_ENV"] = "testing"

import pytest
from fastapi.testclient import TestClient

from app import create_app
from app.extensions import db
from app.models import MeasurementType, User
from app.utils.security import hash_password


class _AppCompat:
    """Lets existing tests keep using `with app.app_context():`."""

    def __init__(self, application):
        self.application = application

    @contextmanager
    def app_context(self):
        # FastAPI endpoints run in worker threads with their own scoped Session.
        # Drop this thread's session before and after so queries see fresh data.
        db.session.remove()
        try:
            yield self.application
        finally:
            db.session.remove()


@pytest.fixture()
def client():
    application = create_app("testing")
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture()
def app(client):
    return _AppCompat(client.app)


def ensure_type(code, name, category, unit, **extra):
    """Return an existing measurement type or create it (safe with startup seeding)."""
    item = MeasurementType.query.filter_by(code=code).first()
    if item:
        return item
    item = MeasurementType(code=code, name=name, category=category, unit=unit, **extra)
    db.session.add(item)
    db.session.commit()
    return item


@pytest.fixture()
def admin_user(app):
    user = User(
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("Secret123!"),
        full_name="Test Administrator",
        role="admin",
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def auth_headers(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin", "password": "Secret123!"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
