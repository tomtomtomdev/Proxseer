import os
from pathlib import Path

PROXY_PORT = int(os.environ.get("PROXSEER_PROXY_PORT", 8080))
WEB_PORT = int(os.environ.get("PROXSEER_WEB_PORT", 9000))

DATA_DIR = Path(os.environ.get("PROXSEER_DATA_DIR", Path.home() / ".proxseer"))
DB_PATH = DATA_DIR / "proxseer.db"

MAX_BODY_SIZE = 1 * 1024 * 1024  # 1 MB

BINARY_CONTENT_TYPES = (
    "image/", "video/", "audio/", "application/octet-stream",
    "application/zip", "application/gzip", "application/pdf",
    "font/", "application/x-font",
)

STATIC_DIR = Path(__file__).parent / "static"
