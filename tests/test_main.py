import pytest
import time
from fastapi.testclient import TestClient
import app.main

# Initialize the test runner client
client = TestClient(app.main.app)

@pytest.fixture(autouse=True)
def force_canary_environment():
    """Fixture to ensure the app runs in canary mode with clean chaos state for every test."""
    original_mode = app.main.MODE
    app.main.MODE = "canary"
    app.main.chaos_state = {"mode": None}
    yield
    # Clean up and reset environment state after test finishes
    app.main.MODE = original_mode
    app.main.chaos_state = {"mode": None}

def test_root_endpoint_message_and_headers():
    """1. Checks root endpoint returns correct text and headers in Canary mode."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("X-Mode") == "canary"
    assert "Welcome to SwiftDeploy Service" in response.json()["message"]

def test_healthz_endpoint_data():
    """2. Verifies the healthz payload delivers correct metadata keys."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "uptime_seconds" in response.json()

def test_chaos_endpoint_activates_error_injection():
    """3. Assures POST /chaos state-machine correctly parses error rates."""
    response = client.post("/chaos", json={"mode": "error", "rate": 0.85})
    assert response.status_code == 200
    assert "chaos activated: error rate 85%" in response.json()["message"]
    assert app.main.chaos_state["mode"] == "error"
    assert app.main.chaos_state["rate"] == 0.85

def test_chaos_middleware_injects_500_errors():
    """4. Confirms that a 100% error rate locks down the middleware with 500s."""
    client.post("/chaos", json={"mode": "error", "rate": 1.0})
    response = client.get("/")
    assert response.status_code == 500
    assert response.json()["error"] == "chaos-induced failure"

def test_chaos_endpoint_activates_slow_injection():
    """5. Assures POST /chaos sets state-machine variables for slow lag delay."""
    response = client.post("/chaos", json={"mode": "slow", "duration": 2})
    assert response.status_code == 200
    assert "chaos activated: slow mode for 2s per request" in response.json()["message"]
    assert app.main.chaos_state["mode"] == "slow"
    assert app.main.chaos_state["duration"] == 2
    assert "until" in app.main.chaos_state

def test_chaos_middleware_injects_slow_latency():
    """6. Assures that slow latency actually forces requests to take time."""
    # Activate slow chaos mode injecting a 1-second delay per request
    client.post("/chaos", json={"mode": "slow", "duration": 1})
    
    start_time = time.time()
    response = client.get("/healthz")
    elapsed_time = time.time() - start_time
    
    assert response.status_code == 200
    # The request should take at least 1 full second due to asyncio.sleep
    assert elapsed_time >= 1.0

def test_chaos_recover_endpoint():
    """7. Verifies that turning on 'recover' cleans the internal app dict state."""
    # Set chaos active first
    client.post("/chaos", json={"mode": "error", "rate": 1.0})
    # Recover it
    response = client.post("/chaos", json={"mode": "recover"})
    assert response.status_code == 200
    assert "chaos cancelled — service recovered" in response.json()["message"]
    assert app.main.chaos_state.get("mode") is None

def test_prometheus_metrics_registry_output():
    """8. Checks that the custom registry endpoint correctly prints scraped metrics."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds_bucket" in response.text
    assert "app_uptime_seconds" in response.text
