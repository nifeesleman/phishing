from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


_BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_DIR / ".env")
load_dotenv(_BACKEND_DIR.parent / ".env", override=False)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def _default_cors_origins() -> list[str]:
    origins: list[str] = []
    for host in ("localhost", "127.0.0.1"):
        for port in (3000, 3001, 3002, 3003, 3004, 3005, 8080):
            origins.append(f"http://{host}:{port}")
    return origins


def _cors_origins(value: str | None) -> list[str]:
    origins: list[str] = []
    for origin in [*_as_list(value), *_default_cors_origins()]:
        if origin not in origins:
            origins.append(origin)
    return origins


def _trusted_domains(value: str | None) -> list[str]:
    defaults = [
        "amazon.com",
        "apple.com",
        "chatgpt.com",
        "facebook.com",
        "github.com",
        "google.com",
        "microsoft.com",
        "openai.com",
        "paypal.com",
        "stripe.com",
        "wikipedia.org",
        "youtube.com",
    ]
    domains: list[str] = []
    for domain in [*_as_list(value), *defaults]:
        normalized = domain.strip().strip(".").lower()
        if normalized and normalized not in domains:
            domains.append(normalized)
    return domains


def _resolve_path(base_dir: Path, value: str) -> str:
    path = Path(value)
    return str(path if path.is_absolute() else base_dir / path)


class Settings:
    BASE_DIR = _BACKEND_DIR
    INSTANCE_DIR = BASE_DIR / "instance"
    TESTING = _as_bool(os.getenv("TESTING"))
    DEBUG = _as_bool(os.getenv("FLASK_DEBUG"))
    JSON_SORT_KEYS = False
    PROPAGATE_EXCEPTIONS = False

    MODEL_PATH = _resolve_path(BASE_DIR, os.getenv("MODEL_PATH", "phishing_model.pkl"))
    VECTORIZER_PATH = _resolve_path(BASE_DIR, os.getenv("VECTORIZER_PATH", "vectorizer.pkl"))
    MODEL_VERSION = os.getenv("MODEL_VERSION", "decision-tree-v1")

    SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))
    SUPABASE_SCANS_TABLE = os.getenv("SUPABASE_SCANS_TABLE", "scans")
    SUPABASE_TIMEOUT_SECONDS = int(os.getenv("SUPABASE_TIMEOUT_SECONDS", "10"))
    SITE_AVAILABILITY_TIMEOUT_SECONDS = float(os.getenv("SITE_AVAILABILITY_TIMEOUT_SECONDS", "5"))
    ADMIN_ANALYTICS_FETCH_LIMIT = int(os.getenv("ADMIN_ANALYTICS_FETCH_LIMIT", "5000"))
    LOCAL_HISTORY_DB_PATH = _resolve_path(BASE_DIR, os.getenv("LOCAL_HISTORY_DB_PATH", "instance/scan_history.sqlite"))
    CORS_ALLOWED_ORIGINS = _cors_origins(os.getenv("CORS_ALLOWED_ORIGINS"))

    SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
    SUPABASE_JWKS_URL = os.getenv("SUPABASE_JWKS_URL", "")
    SUPABASE_JWT_AUDIENCE = os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated")
    SUPABASE_ISSUER = os.getenv("SUPABASE_ISSUER", "")
    SUPABASE_JWT_ALGORITHMS = _as_list(os.getenv("SUPABASE_JWT_ALGORITHMS")) or ["RS256"]

    ADMIN_ROLES = _as_list(os.getenv("ADMIN_ROLES", "admin,service_role"))
    ADMIN_EMAILS = _as_list(os.getenv("ADMIN_EMAILS"))
    TRUSTED_DOMAINS = _trusted_domains(os.getenv("TRUSTED_DOMAINS"))

    BRAND_KEYWORDS = {
        "facebook": "Facebook",
        "paypal": "PayPal",
        "microsoft": "Microsoft",
        "google": "Google",
        "github": "GitHub",
        "chatgpt": "ChatGPT",
        "openai": "OpenAI",
        "apple": "Apple",
        "steam": "Steam",
        "amazon": "Amazon",
        "youtube": "YouTube",
        "wikipedia": "Wikipedia",
        "stripe": "Stripe",
        "mastercard": "Mastercard",
        "americanexpress": "American Express",
        "amex": "American Express",
        "irs": "Internal Revenue Service",
        "ebay": "eBay, Inc.",
        "orange": "Orange",
    }
