"""Backend configuration: paths, environment, and local service URLs."""
import os
from pathlib import Path

PORTAL_ROOT = Path(os.environ.get("BIGWELD_PORTAL_ROOT", "/datapool/bigweld-portal"))

KROKI_URL = os.environ.get("KROKI_URL", "http://127.0.0.1:8889")

ALLOWED_EMAIL = os.environ.get(
    "BIGWELD_ALLOWED_EMAIL",
    "alexanderjcarlson@gmail.com",
)
CF_ACCESS_AUD = os.environ.get(
    "BIGWELD_CF_ACCESS_AUD",
    "6048a086-c0f3-4418-8f58-68993da0959e",
)
CF_ACCESS_ISSUER = os.environ.get(
    "BIGWELD_CF_ACCESS_ISSUER",
    "https://ninerealmsme.cloudflareaccess.com",
)
CF_ACCESS_CERTS_URL = os.environ.get(
    "BIGWELD_CF_ACCESS_CERTS_URL",
    "https://ninerealmsme.cloudflareaccess.com/cdn-cgi/access/certs",
)
CF_ACCESS_CERTS_TTL_S = int(os.environ.get("BIGWELD_CF_ACCESS_CERTS_TTL_S", "300"))

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_OUTPUT_BYTES = 10 * 1024 * 1024

SUMMARIZE_IDLE_THRESHOLD_S = 24 * 60 * 60
