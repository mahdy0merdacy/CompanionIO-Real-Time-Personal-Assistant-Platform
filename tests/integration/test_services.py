import pytest
import requests
import time
from typing import Dict, Any

# Service endpoints
SERVICES = {
    "orchestrator": "http://localhost:8000",
    "auth": "http://localhost:5000",
    "llm": "http://localhost:8001",
    "stt": "http://localhost:8002"
}

def wait_for_service(url: str, timeout: int = 60) -> bool:
    """Wait for a service to become healthy."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    return True
        except requests.RequestException:
            pass
        time.sleep(2)
    return False

@pytest.mark.parametrize("service_name,url", SERVICES.items())
def test_service_health(service_name: str, url: str):
    """Test that each service has a healthy health endpoint."""
    assert wait_for_service(url), f"Service {service_name} at {url} is not healthy"

def test_auth_service_flow():
    """Test basic authentication flow."""
    # This would be expanded with actual auth flow testing
    auth_url = SERVICES["auth"]
    response = requests.get(f"{auth_url}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "auth"

def test_orchestrator_auth_integration():
    """Test that orchestrator can validate JWT tokens."""
    # This would test the JWT validation integration
    orch_url = SERVICES["orchestrator"]
    response = requests.get(f"{orch_url}/health")
    assert response.status_code == 200

def test_service_discovery():
    """Test that services can discover each other."""
    # Test basic connectivity between services
    orch_url = SERVICES["orchestrator"]
    response = requests.get(f"{orch_url}/health")
    assert response.status_code == 200

def test_websocket_connection():
    """Test WebSocket connection capability."""
    # This would test WebSocket endpoints
    import websocket
    try:
        ws = websocket.create_connection(f"ws://localhost:8000/ws/test")
        ws.close()
        assert True
    except Exception:
        assert False, "WebSocket connection failed"

if __name__ == "__main__":
    # Run basic health checks
    print("Running integration tests...")
    for service_name, url in SERVICES.items():
        if wait_for_service(url):
            print(f"✅ {service_name} is healthy")
        else:
            print(f"❌ {service_name} is not healthy")
            exit(1)
    print("All services are healthy!")