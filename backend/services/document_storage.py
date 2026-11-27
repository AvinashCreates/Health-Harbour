import base64
import hashlib
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


ENCRYPTION_MAGIC = b"HHENC1\x00"


class EncryptionConfigurationError(RuntimeError):
    pass


class LocalDocumentStorage:
    def __init__(self, root: Path | None = None):
        configured = os.getenv("FILE_STORAGE_PATH", "uploads")
        path = root if root is not None else Path(configured)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[1] / path
        self.root = path.resolve()

    def ensure_root(self) -> None:
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)

    def path_for(self, storage_key: str) -> Path:
        if not storage_key or storage_key in {".", ".."} or Path(storage_key).name != storage_key:
            raise ValueError("Invalid document storage key")
        return self.root / storage_key

    def _encryption_key(self) -> tuple[bytes, str]:
        encoded = os.getenv("DOCUMENT_ENCRYPTION_KEY", "").strip()
        if not encoded:
            raise EncryptionConfigurationError("DOCUMENT_ENCRYPTION_KEY is required when document encryption is enabled")
        try:
            key = base64.b64decode(encoded, validate=True)
        except Exception:
            try:
                key = bytes.fromhex(encoded)
            except Exception as exc:
                raise EncryptionConfigurationError("DOCUMENT_ENCRYPTION_KEY must be base64 or hexadecimal") from exc
        if len(key) != 32:
            raise EncryptionConfigurationError("DOCUMENT_ENCRYPTION_KEY must encode exactly 32 bytes")
        key_id = hashlib.sha256(key).hexdigest()[:32]
        return key, key_id

    def write_new(self, storage_key: str, content: bytes) -> tuple[Path, str | None, str | None]:
        self.ensure_root()
        path = self.path_for(storage_key)
        encryption_required = os.getenv("DOCUMENT_ENCRYPTION_REQUIRED", "false").strip().lower() == "true"
        if encryption_required:
            key, key_id = self._encryption_key()
            nonce = os.urandom(12)
            ciphertext = AESGCM(key).encrypt(nonce, content, storage_key.encode("utf-8"))
            payload = ENCRYPTION_MAGIC + nonce + ciphertext
            with path.open("xb") as stored:
                stored.write(payload)
            path.chmod(0o600)
            return path, "AES-256-GCM-v1", key_id
        with path.open("xb") as stored:
            stored.write(content)
        path.chmod(0o600)
        return path, None, None

    def read_authorized(
        self,
        storage_key: str,
        encryption_version: str | None,
        encryption_key_id: str | None,
    ) -> bytes:
        path = self.path_for(storage_key)
        payload = path.read_bytes()
        if encryption_version is None:
            return payload
        if encryption_version != "AES-256-GCM-v1":
            raise EncryptionConfigurationError("Unsupported document encryption metadata")
        if not payload.startswith(ENCRYPTION_MAGIC):
            raise EncryptionConfigurationError("Encrypted document payload has invalid framing")
        if not encryption_key_id:
            raise EncryptionConfigurationError("Encrypted document is missing key metadata")
        key, key_id = self._encryption_key()
        if key_id != encryption_key_id:
            raise EncryptionConfigurationError("Document encryption key does not match key metadata")
        framed = payload[len(ENCRYPTION_MAGIC):]
        if len(framed) < 28:
            raise EncryptionConfigurationError("Encrypted document payload is truncated")
        nonce, ciphertext = framed[:12], framed[12:]
        try:
            return AESGCM(key).decrypt(nonce, ciphertext, storage_key.encode("utf-8"))
        except Exception as exc:
            raise EncryptionConfigurationError("Document ciphertext is invalid or tampered") from exc

    def exists(self, storage_key: str) -> bool:
        try:
            path = self.path_for(storage_key)
        except ValueError:
            return False
        return path.is_file()

    def remove_to_tombstone(self, storage_key: str, tombstone_name: str) -> tuple[Path, Path]:
        path = self.path_for(storage_key)
        tombstone = path.with_name(tombstone_name)
        if path.exists():
            os.replace(path, tombstone)
        return path, tombstone

    def restore(self, path: Path, tombstone: Path) -> bool:
        if tombstone.exists():
            os.replace(tombstone, path)
            return True
        return False


def get_document_storage() -> LocalDocumentStorage:
    return LocalDocumentStorage()
