import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.document_storage import (
    EncryptionConfigurationError,
    LocalDocumentStorage,
)
from services.document_scanner import ScanResult, UnavailableDocumentScanner


class DocumentSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = LocalDocumentStorage(Path(self.temp_dir.name))
        self.key = os.urandom(32)
        self.key_text = __import__("base64").b64encode(self.key).decode("ascii")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_aes_gcm_round_trip_and_unique_nonces(self):
        with patch.dict(os.environ, {
            "DOCUMENT_ENCRYPTION_REQUIRED": "true",
            "DOCUMENT_ENCRYPTION_KEY": self.key_text,
        }):
            path_a, version_a, key_id_a = self.storage.write_new("document-a.blob", b"synthetic clinical text")
            path_b, version_b, key_id_b = self.storage.write_new("document-b.blob", b"synthetic clinical text")
            self.assertNotEqual(path_a.read_bytes(), path_b.read_bytes())
            self.assertEqual(self.storage.read_authorized("document-a.blob", version_a, key_id_a), b"synthetic clinical text")
            self.assertEqual(self.storage.read_authorized("document-b.blob", version_b, key_id_b), b"synthetic clinical text")

    def test_missing_key_and_wrong_key_fail_closed(self):
        with patch.dict(os.environ, {
            "DOCUMENT_ENCRYPTION_REQUIRED": "true",
            "DOCUMENT_ENCRYPTION_KEY": "",
        }, clear=False):
            with self.assertRaises(EncryptionConfigurationError):
                self.storage.write_new("missing-key.blob", b"plaintext must not be stored")

        with patch.dict(os.environ, {
            "DOCUMENT_ENCRYPTION_REQUIRED": "true",
            "DOCUMENT_ENCRYPTION_KEY": self.key_text,
        }):
            path, version, key_id = self.storage.write_new("wrong-key.blob", b"sensitive synthetic text")
        wrong_key = __import__("base64").b64encode(os.urandom(32)).decode("ascii")
        with patch.dict(os.environ, {
            "DOCUMENT_ENCRYPTION_REQUIRED": "true",
            "DOCUMENT_ENCRYPTION_KEY": wrong_key,
        }):
            with self.assertRaises(EncryptionConfigurationError):
                self.storage.read_authorized("wrong-key.blob", version, key_id)
        self.assertFalse(b"sensitive synthetic text" in path.read_bytes())

    def test_ciphertext_tampering_is_detected(self):
        with patch.dict(os.environ, {
            "DOCUMENT_ENCRYPTION_REQUIRED": "true",
            "DOCUMENT_ENCRYPTION_KEY": self.key_text,
        }):
            path, version, key_id = self.storage.write_new("tamper.blob", b"integrity protected")
            payload = bytearray(path.read_bytes())
            payload[-1] ^= 1
            path.write_bytes(payload)
            with self.assertRaises(EncryptionConfigurationError):
                self.storage.read_authorized("tamper.blob", version, key_id)

    def test_plaintext_legacy_record_is_not_reinterpreted_as_encrypted(self):
        path, version, key_id = self.storage.write_new("legacy.blob", b"existing unencrypted record")
        self.assertIsNone(version)
        self.assertIsNone(key_id)
        self.assertEqual(self.storage.read_authorized("legacy.blob", version, key_id), b"existing unencrypted record")

    def test_scanner_unavailable_is_fail_closed(self):
        scanner = UnavailableDocumentScanner()
        result = scanner.scan(b"<synthetic>", "record.txt")
        self.assertEqual(result.status, "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
