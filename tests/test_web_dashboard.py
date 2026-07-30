from fastapi.testclient import TestClient

from ticket_sniper.demo.seed import seed_demo_data
from ticket_sniper.web.app import app


def test_dashboard_loads_with_seeded_events(anyio_backend):
    import anyio

    anyio.run(seed_demo_data)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Dodgers Demo" in response.text
    assert "Hollywood Bowl Demo" in response.text
    assert "Default Tix Profile" in response.text
    assert "Dodgers" in response.text


def test_manual_poll_route_runs_prototype_loop(anyio_backend):
    import anyio

    anyio.run(seed_demo_data)
    client = TestClient(app)
    response = client.post("/events/seatgeek/demo-dodgers-001/poll", follow_redirects=True)
    assert response.status_code == 200
    assert "demo-dodgers-001" in response.text
    assert "pass" in response.text
    assert "alert" in response.text
