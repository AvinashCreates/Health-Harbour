import os
import socket
from dataclasses import dataclass


@dataclass(frozen=True)
class ScanResult:
    status: str
    detail: str


class DocumentScanner:
    def scan(self, content: bytes, filename: str) -> ScanResult:
        raise NotImplementedError


class ClamAvScanner(DocumentScanner):
    def scan(self, content: bytes, filename: str) -> ScanResult:
        host = os.getenv("CLAMAV_HOST", "").strip()
        if not host:
            return ScanResult("UNAVAILABLE", "ClamAV host is not configured")
        port = int(os.getenv("CLAMAV_PORT", "3310") or "3310")
        timeout = float(os.getenv("CLAMAV_TIMEOUT_SECONDS", "10") or "10")
        try:
            with socket.create_connection((host, port), timeout=timeout) as connection:
                connection.settimeout(timeout)
                connection.sendall(b"zINSTREAM\x00")
                chunks = content
                connection.sendall(len(chunks).to_bytes(4, "big") + chunks + b"\x00\x00\x00\x00")
                response = b""
                while True:
                    chunk = connection.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if response.endswith(b"\x00"):
                        break
            text = response.decode("utf-8", "replace").strip("\x00")
            if "FOUND" in text:
                return ScanResult("MALICIOUS", "Scanner detected a malicious signature")
            if text.endswith(" OK") or "stream: OK" in text:
                return ScanResult("CLEAN", "Scanner found no malicious signature")
            return ScanResult("UNSUPPORTED", "Scanner returned an unsupported result")
        except socket.timeout:
            return ScanResult("TIMEOUT", "Scanner timed out")
        except (ConnectionError, OSError, ValueError):
            return ScanResult("UNAVAILABLE", "Scanner could not be reached")


class UnavailableDocumentScanner(DocumentScanner):
    def scan(self, content: bytes, filename: str) -> ScanResult:
        return ScanResult("UNAVAILABLE", "Malware scanning is not configured")


def get_document_scanner() -> DocumentScanner:
    adapter = os.getenv("DOCUMENT_SCANNER", "unavailable").strip().lower()
    if adapter == "clamav":
        return ClamAvScanner()
    return UnavailableDocumentScanner()
