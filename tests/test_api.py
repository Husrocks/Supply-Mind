"""
SupplyMind — FastAPI Client Mock Testing
Verifies FastAPI routing registers, endpoints validate payloads, and middlewares execute.
"""

import sys
import os
import unittest

# Configure pathing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from api.main import app
from api.middleware.auth import create_jwt_token

class TestAPIRoutes(unittest.TestCase):
    def setUp(self):
        # Override debug setting to False so that token verification behaves correctly (not bypassing validation)
        from config import settings
        self._old_debug = settings.debug
        settings.debug = False

        self.client = TestClient(app)
        # Generate token keys for roles
        self.admin_token = create_jwt_token("admin_user", "admin")
        self.viewer_token = create_jwt_token("viewer_user", "viewer")

    def tearDown(self):
        from config import settings
        settings.debug = self._old_debug

    def test_health_check(self):
        """Verify the health check endpoint returns 200."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")

    def test_auth_unauthorized_denial(self):
        """Verify missing authorization header triggers 401."""
        response = self.client.get("/api/v1/predictions/risk-context/FOODS_1_001_CA_1_evaluation?supplier_id=SUP-0001")
        self.assertEqual(response.status_code, 401) # Bearer parser throws 401 on missing authorization

    def test_auth_forbidden_role(self):
        """Verify viewer roles are denied access to admin-only audit log routing."""
        headers = {"Authorization": f"Bearer {self.viewer_token}"}
        response = self.client.get("/api/v1/audit/reasoning-log", headers=headers)
        self.assertEqual(response.status_code, 403) # RBAC blocks viewer from admin routing

    def test_error_rfc7807_format(self):
        """Verify client request validation errors yield valid RFC 7807 JSON details schema."""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        # Call trigger cycle route with an invalid payload structure (non-integer current_inventory) to trigger validation error
        response = self.client.post(
            "/api/v1/agent/trigger",
            headers=headers,
            json={"sku_id": "FOODS_1_001", "primary_supplier_id": "SUP-001", "current_inventory": "not_an_int"}
        )
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertIn("title", data)
        self.assertIn("correlation_id", data)
        self.assertEqual(data["status"], 422)

if __name__ == "__main__":
    unittest.main()
