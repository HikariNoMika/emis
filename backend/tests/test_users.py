"""Tests for user creation and self-service profile editing."""

import pytest

from app.models import User


def _create_user(client, auth_headers, username="operator", role="viewer"):
    return client.post(
        "/api/v1/users",
        json={
            "username": username,
            "email": f"{username}@emis.local",
            "full_name": "Test Operator",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "role": role,
            "is_active": True,
        },
        headers=auth_headers,
    )


def test_admin_can_create_and_list_users(client, auth_headers):
    created = _create_user(client, auth_headers)
    assert created.status_code == 201, created.text
    assert created.json()["data"]["role"] == "viewer"
    assert "password" not in created.json()["data"]

    listing = client.get("/api/v1/users", headers=auth_headers)
    assert listing.status_code == 200
    assert listing.json()["meta"]["total"] >= 2


def test_duplicate_username_rejected(client, auth_headers):
    assert _create_user(client, auth_headers).status_code == 201
    duplicate = _create_user(client, auth_headers)
    assert duplicate.status_code == 409


def test_deactivate_and_activate(client, auth_headers):
    user_id = _create_user(client, auth_headers).json()["data"]["id"]

    assert client.post(f"/api/v1/users/{user_id}/deactivate",
                       headers=auth_headers).status_code == 200
    assert client.get(f"/api/v1/users/{user_id}",
                      headers=auth_headers).json()["data"]["is_active"] is False

    assert client.post(f"/api/v1/users/{user_id}/activate",
                       headers=auth_headers).status_code == 200
    assert client.get(f"/api/v1/users/{user_id}",
                      headers=auth_headers).json()["data"]["is_active"] is True


def test_reset_password(client, auth_headers):
    user_id = _create_user(client, auth_headers).json()["data"]["id"]
    response = client.post(
        f"/api/v1/users/{user_id}/reset-password",
        json={"new_password": "NewPassword123!", "confirm_password": "NewPassword123!"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    login = client.post("/api/v1/auth/login", json={
        "identifier": "operator", "password": "NewPassword123!",
    })
    assert login.status_code == 200


def test_user_can_edit_own_profile(client, auth_headers):
    _create_user(client, auth_headers)
    login = client.post("/api/v1/auth/login", json={
        "identifier": "operator", "password": "Password123!",
    }).json()
    headers = {"Authorization": f"Bearer {login['data']['access_token']}"}

    response = client.put("/api/v1/auth/profile", json={
        "full_name": "Updated Operator", "email": "operator.new@emis.local",
    }, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["full_name"] == "Updated Operator"


def test_non_admin_cannot_manage_users(client, auth_headers):
    _create_user(client, auth_headers)
    login = client.post("/api/v1/auth/login", json={
        "identifier": "operator", "password": "Password123!",
    }).json()
    headers = {"Authorization": f"Bearer {login['data']['access_token']}"}

    assert client.get("/api/v1/users", headers=headers).status_code == 400
