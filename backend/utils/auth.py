from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from functools import lru_cache
from threading import Lock

import jwt
import requests
from flask import current_app, request
from jwt import InvalidTokenError, PyJWKClient
from jwt.exceptions import PyJWKClientError

from utils.errors import AuthenticationError, AuthorizationError, ConfigurationError

# Thread-safe in-memory cache: token_hash -> (claims, monotonic_expiry)
_token_claims_cache: dict[str, tuple[dict, float]] = {}
_token_cache_lock = Lock()
_MAX_TOKEN_CACHE_SIZE = 500
_MAX_CACHE_TTL = 300.0  # cap at 5 minutes even if token is longer-lived


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _get_cached_claims(token: str) -> dict | None:
    key = _token_hash(token)
    now = time.monotonic()
    with _token_cache_lock:
        entry = _token_claims_cache.get(key)
        if entry is not None:
            claims, expiry = entry
            if now < expiry:
                return claims
            del _token_claims_cache[key]
    return None


def _set_cached_claims(token: str, claims: dict) -> None:
    exp = claims.get("exp")
    if isinstance(exp, (int, float)):
        ttl = max(0.0, float(exp) - time.time())
    else:
        ttl = _MAX_CACHE_TTL
    ttl = min(ttl, _MAX_CACHE_TTL)
    if ttl <= 0:
        return

    key = _token_hash(token)
    now = time.monotonic()
    with _token_cache_lock:
        if len(_token_claims_cache) >= _MAX_TOKEN_CACHE_SIZE:
            expired = [k for k, (_, ex) in _token_claims_cache.items() if ex <= now]
            for k in expired:
                del _token_claims_cache[k]
        _token_claims_cache[key] = (claims, now + ttl)


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str | None
    claims: dict
    is_admin: bool
    access_token: str | None = None


@lru_cache(maxsize=4)
def _build_jwk_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


class SupabaseJWTVerifier:
    def __init__(self, config) -> None:
        self._config = config

    def require_user(self) -> AuthenticatedUser:
        auth_header = request.headers.get("Authorization", "").strip()
        if not auth_header.startswith("Bearer "):
            raise AuthenticationError("Missing Bearer token")

        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            raise AuthenticationError("Missing Bearer token")

        claims = self._decode_token(token)
        user_id = claims.get("sub")
        if not user_id:
            raise AuthenticationError("Bearer token is missing subject claim")

        email = claims.get("email")
        return AuthenticatedUser(
            user_id=user_id,
            email=email,
            claims=claims,
            is_admin=self._is_admin(claims, email),
            access_token=token,
        )

    def require_admin(self) -> AuthenticatedUser:
        user = self.require_user()
        if not user.is_admin:
            raise AuthorizationError("Admin privileges are required")
        return user

    def _decode_token(self, token: str) -> dict:
        cached = _get_cached_claims(token)
        if cached is not None:
            return cached
        claims = self._decode_token_uncached(token)
        _set_cached_claims(token, claims)
        return claims

    def _decode_token_uncached(self, token: str) -> dict:
        issuer = self._config["SUPABASE_ISSUER"] or None
        audience = self._config["SUPABASE_JWT_AUDIENCE"] or None
        verify_audience = audience is not None

        try:
            if self._config["SUPABASE_JWT_SECRET"]:
                return jwt.decode(
                    token,
                    self._config["SUPABASE_JWT_SECRET"],
                    algorithms=self._config["SUPABASE_JWT_ALGORITHMS"],
                    audience=audience,
                    issuer=issuer,
                    options={"verify_aud": verify_audience},
                )

            jwks_url = self._config["SUPABASE_JWKS_URL"]
            if not jwks_url:
                raise ConfigurationError("Supabase JWT verification is not configured")

            signing_key = _build_jwk_client(jwks_url).get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=self._config["SUPABASE_JWT_ALGORITHMS"],
                audience=audience,
                issuer=issuer,
                options={"verify_aud": verify_audience},
            )
        except (InvalidTokenError, PyJWKClientError):
            return self._fetch_user_claims(token)

    def _fetch_user_claims(self, token: str) -> dict:
        publishable_key = self._config["SUPABASE_PUBLISHABLE_KEY"]
        supabase_url = self._config["SUPABASE_URL"]
        if not publishable_key or not supabase_url:
            raise AuthenticationError("Invalid bearer token")

        try:
            response = requests.get(
                f"{supabase_url}/auth/v1/user",
                headers={
                    "apikey": publishable_key,
                    "Authorization": f"Bearer {token}",
                },
                timeout=10,
            )
        except requests.RequestException as exc:
            raise AuthenticationError("Unable to validate bearer token") from exc

        if response.status_code >= 400:
            raise AuthenticationError("Invalid bearer token")

        payload = response.json()
        user_id = payload.get("id")
        if not user_id:
            raise AuthenticationError("Invalid bearer token")

        app_metadata = payload.get("app_metadata") if isinstance(payload.get("app_metadata"), dict) else {}
        role = payload.get("role") or app_metadata.get("role") or "authenticated"
        return {
            "sub": user_id,
            "email": payload.get("email"),
            "role": role,
            "app_metadata": app_metadata,
            "user_metadata": payload.get("user_metadata") if isinstance(payload.get("user_metadata"), dict) else {},
        }

    def _is_admin(self, claims: dict, email: str | None) -> bool:
        roles = {str(claims.get("role", "")).lower()}
        app_metadata = claims.get("app_metadata") or {}
        if isinstance(app_metadata, dict):
            roles.add(str(app_metadata.get("role", "")).lower())
            for entry in app_metadata.get("roles", []) or []:
                roles.add(str(entry).lower())

        return bool(roles & set(self._config["ADMIN_ROLES"])) or bool(
            email and email.lower() in set(self._config["ADMIN_EMAILS"])
        )


def get_jwt_verifier() -> SupabaseJWTVerifier:
    verifier = current_app.extensions.get("jwt_verifier")
    if verifier is None:
        raise ConfigurationError("JWT verifier is unavailable")
    return verifier
