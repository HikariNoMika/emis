"""Tests for Phase 1 authentication and system endpoints."""


def test_health_endpoint_is_public(client):
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["api_version"] == "v1"


def test_login_success_returns_tokens(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin", "password": "Secret123!"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["username"] == "admin"
    assert "password_hash" not in data["user"]


def test_login_by_email_also_works(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin@example.com", "password": "Secret123!"},
    )
    assert response.status_code == 200


def test_login_with_wrong_password_fails(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["success"] is False


def test_login_validation_error(client):
    response = client.post("/api/v1/auth/login", json={"password": "x"})
    assert response.status_code == 400
    assert "errors" in response.json()


def test_me_requires_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["username"] == "admin"


def test_change_password(client, auth_headers):
    response = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={
            "current_password": "Secret123!",
            "new_password": "NewSecret456!",
            "confirm_password": "NewSecret456!",
        },
    )
    assert response.status_code == 200

    # The old password should no longer work.
    old_login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin", "password": "Secret123!"},
    )
    assert old_login.status_code == 401


def test_logout_revokes_access_token(client, auth_headers):
    logout = client.post("/api/v1/auth/logout", headers=auth_headers)
    assert logout.status_code == 200

    me = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me.status_code == 401


def test_settings_round_trip(client, auth_headers):
    payload = {
        "key": "station_status_thresholds",
        "value": {"delayed_minutes": 45, "offline_minutes": 180},
    }
    put = client.put(
        "/api/v1/system/settings", headers=auth_headers, json=payload
    )
    assert put.status_code == 200

    get = client.get("/api/v1/system/settings", headers=auth_headers)
    assert get.json()["data"]["station_status_thresholds"]["delayed_minutes"] == 45


def test_audit_logs_are_recorded(client, auth_headers):
    response = client.get("/api/v1/audit-logs", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] >= 1
    assert any(log["action"] == "LOGIN" for log in body["data"])
