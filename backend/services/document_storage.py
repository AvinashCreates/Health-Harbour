import os
from pathlib import Path


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

    def write_new(self, storage_key: str, content: bytes) -> Path:
        self.ensure_root()
        path = self.path_for(storage_key)
        with path.open("xb") as stored:
            stored.write(content)
        path.chmod(0o600)
        return path

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
