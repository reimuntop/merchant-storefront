import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

AUTH_TOKEN_SECRET = os.getenv("AUTH_TOKEN_SECRET") or "local-dev-secret"
AUTH_TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "43200"))
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
