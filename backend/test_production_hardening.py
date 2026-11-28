import os
import unittest
from unittest.mock import patch

import main


class ProductionStartupConfigurationTests(unittest.TestCase):
    def _production_environment(self):
        return {
            "APP_ENV": "production",
            "DATABASE_URL": "postgresql+psycopg2://healthapp:synthetic@db:5432/healthcare_exchange",
            "CORS_ORIGINS": "https://demo.healthharbor.example",
            "TRUSTED_HOSTS": "demo.healthharbor.example",
            "JWT_SECRET": "a-unique-production-secret-that-is-at-least-32-characters",
            "DOCUMENT_ENCRYPTION_REQUIRED": "true",
            "DOCUMENT_ENCRYPTION_KEY": "b" * 64,
            "DOCUMENT_SCAN_REQUIRED": "true",
            "DOCUMENT_SCANNER": "clamav",
            "CLAMAV_HOST": "clamav.internal",
            "AUTH_PROVIDER": "local",
            "FHIR_MODE": "local",
            "FABRIC_ENABLED": "false",
        }

    def test_production_configuration_accepts_explicit_safe_settings(self):
        environment = self._production_environment()
        with patch.dict(os.environ, environment, clear=False):
            with patch.object(main, "DATABASE_URL", environment["DATABASE_URL"]):
                main._validate_production_configuration()

    def test_production_rejects_sqlite(self):
        environment = self._production_environment()
        environment["DATABASE_URL"] = "sqlite:///./healthcare.db"
        with patch.dict(os.environ, environment, clear=False):
            with patch.object(main, "DATABASE_URL", environment["DATABASE_URL"]):
                with self.assertRaises(RuntimeError):
                    main._validate_production_configuration()

    def test_production_rejects_cors_wildcard_and_loopback_origins(self):
        for value in ("*", "http://localhost:5173"):
            environment = self._production_environment()
            environment["CORS_ORIGINS"] = value
            with patch.dict(os.environ, environment, clear=False):
                with patch.object(main, "DATABASE_URL", environment["DATABASE_URL"]):
                    with self.assertRaises(RuntimeError):
                        main._validate_production_configuration()

    def test_production_requires_encryption_key_and_clamav(self):
        environment = self._production_environment()
        environment["DOCUMENT_ENCRYPTION_KEY"] = ""
        with patch.dict(os.environ, environment, clear=False):
            with patch.object(main, "DATABASE_URL", environment["DATABASE_URL"]):
                with self.assertRaises(RuntimeError):
                    main._validate_production_configuration()

        environment = self._production_environment()
        environment["CLAMAV_HOST"] = ""
        with patch.dict(os.environ, environment, clear=False):
            with patch.object(main, "DATABASE_URL", environment["DATABASE_URL"]):
                with self.assertRaises(RuntimeError):
                    main._validate_production_configuration()


if __name__ == "__main__":
    unittest.main()
