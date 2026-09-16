"""US-001 acceptance criterion: app boots, health endpoint returns 200."""


def test_health_returns_ok(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
