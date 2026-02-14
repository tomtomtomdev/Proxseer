import os
import socket
from pathlib import Path

PROXY_PORT = int(os.environ.get("PROXSEER_PROXY_PORT", 8080))
WEB_PORT = int(os.environ.get("PROXSEER_WEB_PORT", 9000))

DATA_DIR = Path(os.environ.get("PROXSEER_DATA_DIR", Path.home() / ".proxseer"))
DB_PATH = DATA_DIR / "proxseer.db"

MAX_BODY_SIZE = 1 * 1024 * 1024  # 1 MB

# Domains using certificate pinning – mitmproxy will pass these through
# without intercepting TLS.  Override with a comma-separated list of regex
# patterns via PROXSEER_IGNORE_HOSTS.
_DEFAULT_IGNORE_HOSTS = [
    r".*\.linkedin\.com",
    r".*\.apple\.com",
    r".*\.icloud\.com",
    r".*\.mzstatic\.com",
]

_env_ignore = os.environ.get("PROXSEER_IGNORE_HOSTS", "")
IGNORE_HOSTS = (
    [p.strip() for p in _env_ignore.split(",") if p.strip()]
    if _env_ignore
    else _DEFAULT_IGNORE_HOSTS
)

BINARY_CONTENT_TYPES = (
    "image/", "video/", "audio/", "application/octet-stream",
    "application/zip", "application/gzip", "application/pdf",
    "font/", "application/x-font",
)

STATIC_DIR = Path(__file__).parent / "static"


def find_available_port(preferred: int, max_attempts: int = 50) -> int:
    """Return *preferred* if it is free, otherwise try successive ports."""
    for offset in range(max_attempts):
        port = preferred + offset
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))
                return port
        except OSError:
            continue
    raise RuntimeError(
        f"Could not find an available port in range "
        f"{preferred}–{preferred + max_attempts - 1}"
    )
