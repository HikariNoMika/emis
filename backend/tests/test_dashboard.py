"""Dashboard endpoints must return real database values, never placeholders."""


def test_summary_counts_real_stations(client, auth_headers, app):
    from app.extensions import db
    from app.models import Sensor, Station

    with app.app_context():
        db.session.add(
            Station(station_code="TEST-001", name="Test Station", timezone="Asia/Manila")
        )
        db.session.commit()
        station = Station.query.filter_by(station_code="TEST-001").first()
        db.session.add(
            Sensor(station_id=station.id, name="Test Sensor", port_number="1")
        )
        db.session.commit()

    response = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_stations"] == 1
    assert data["total_sensors"] == 1
    assert data["active_alerts"] == 0


def test_environmental_summary_is_empty_when_no_measurements(client, auth_headers):
    response = client.get(
        "/api/v1/dashboard/environmental-summary", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["data"] == []
