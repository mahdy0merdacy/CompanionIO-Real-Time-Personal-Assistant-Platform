from locust import HttpUser, task, between
import json

class CompanionIOUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def health_check(self):
        """Test health endpoint."""
        self.client.get("/health")

    @task(2)
    def get_sessions(self):
        """Test session listing (requires auth in real scenario)."""
        self.client.get("/sessions")

    @task(1)
    def websocket_connect(self):
        """Test WebSocket connection."""
        # Note: Locust has limited WebSocket support
        # This would need custom implementation for full WebSocket testing
        pass

    @task(1)
    def auth_health(self):
        """Test auth service health."""
        # This would test cross-service calls
        pass

    def on_start(self):
        """Setup before starting tasks."""
        # In a real scenario, this would authenticate and get JWT token
        # self.jwt_token = self.authenticate()
        pass

    def authenticate(self):
        """Mock authentication - would call auth service in real test."""
        # This would be implemented to get a real JWT token
        return "mock-jwt-token"