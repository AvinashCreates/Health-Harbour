import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import main


class HealthEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()

    def test_liveness_never_requires_external_integrations(self):
        with patch.dict(os.environ, {
            "FHIR_MODE": "hapi",
            "DOCUMENT_SCAN_REQUIRED": "true",
            "FABRIC_ENABLED": "true",
        }, clear=False):
            response = self.client.get("/health/live")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "alive")

    def test_readiness_reports_database_and_optional_component_state_without_secrets(self):
        with patch.dict(os.environ, {
            "FHIR_MODE": "local",
            "DOCUMENT_SCAN_REQUIRED": "false",
            "DOCUMENT_ENCRYPTION_REQUIRED": "false",
            "FABRIC_ENABLED": "false",
        }, clear=False):
            response = self.client.get("/health/ready")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["components"]["database"])
        self.assertNotIn("secret", str(body).lower())


if __name__ == "__main__":
    unittest.main()
