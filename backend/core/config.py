"""Backend configuration: paths, environment, and local service URLs."""
import os
from pathlib import Path

PORTAL_ROOT = Path(os.environ.get("BIGWELD_PORTAL_ROOT", "/datapool/bigweld-portal"))

KROKI_URL = os.environ.get("KROKI_URL", "http://127.0.0.1:8889")

ALLOWED_EMAIL = os.environ.get(
    "BIGWELD_ALLOWED_EMAIL",
    "alexanderjcarlson@gmail.com",
)

SUMMARIZE_IDLE_THRESHOLD_S = 24 * 60 * 60
