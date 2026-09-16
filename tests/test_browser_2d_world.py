import math

from fastapi.testclient import TestClient

from examples.browser_2d_world.app import create_app
from examples.browser_2d_world.world import WorldAdapter, WorldState, advance_world


def test_world_adapter_and_motion_are_explicit_and_bounded():
    adapter = WorldAdapter()
    world = WorldState(light_x=10.0, light_y=0.0)
    encoded = adapter.encode(world.as_dict())

    assert 0 <= encoded["vision"]["left"] <= 1
    assert 0 <= encoded["vision"]["right"] <= 1
    assert encoded["vision"]["left"] == encoded["vision"]["right"]

    action = adapter.decode({
        "mean_rate_hz": 50.0,
        "left_rate_hz": 60.0,
        "right_rate_hz": 40.0,
    })
    assert action == {"speed": 0.5, "rotation": 0.2}

    before = (world.x, world.y, world.heading)
    advance_world(world, action)
    assert (world.x, world.y, world.heading) != before
    assert math.isfinite(world.heading)


def test_browser_world_api_synthetic():
    with TestClient(create_app(dataset="synthetic")) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "FlyBrain 2D World" in page.text

        state = client.get("/api/world/state").json()
        assert state["dataset"] == "synthetic"
        assert state["world"]["light_x"] == 10.0
        assert "validated biological motor commands" in state["labels"]["action"]

        response = client.post(
            "/api/world/step",
            json={"light_x": -5.0, "light_y": 4.0, "brain_ms": 10},
            headers={"Origin": "http://testserver"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["world"]["light_x"] == -5.0
        assert payload["brain"]["time_ms"] == 10
        assert 0 <= payload["input"]["left"] <= 1
        assert 0 <= payload["input"]["right"] <= 1
        assert payload["brain"]["spikes"] >= 0
        assert "speed" in payload["action"]
        assert "rotation" in payload["action"]

        reset = client.post("/api/world/reset", json={}).json()
        assert reset["world"]["x"] == 0.0
        assert reset["world"]["y"] == 0.0
        assert reset["world"]["light_x"] == 10.0
        assert reset["world"]["light_y"] == 5.0


def test_browser_world_rejects_cross_origin_and_bad_coordinates():
    with TestClient(create_app(dataset="synthetic")) as client:
        blocked = client.post(
            "/api/world/reset",
            json={},
            headers={"Origin": "https://example.com"},
        )
        assert blocked.status_code == 403

        invalid = client.post(
            "/api/world/step",
            json={"light_x": 99.0, "light_y": 0.0, "brain_ms": 10},
        )
        assert invalid.status_code == 422
