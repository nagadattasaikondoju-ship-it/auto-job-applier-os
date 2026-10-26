import logging
import time
import uuid
from typing import Any

import httpx
import jwt
from cryptography.x509 import load_pem_x509_certificate
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from packages.core.config import settings

logger = logging.getLogger("applyon.auth")

security = HTTPBearer(auto_error=False)

# Cached JWKS keys from Google/Firebase
_JWKS_CACHE: dict[str, Any] = {}
_JWKS_EXPIRY: float = 0


class AuthenticatedUser(BaseModel):
    user_id: str
    email: str | None = None
    role: str = "authenticated"
    claims: dict[str, Any] = {}

    @property
    def id(self) -> uuid.UUID:
        try:
            return uuid.UUID(self.user_id)
        except Exception:
            return uuid.uuid5(uuid.NAMESPACE_DNS, self.user_id)


async def fetch_firebase_public_keys() -> dict[str, str]:
    """Fetch and cache Google's public x509 certs for Firebase Auth."""
    global _JWKS_CACHE, _JWKS_EXPIRY
    now = time.time()
    if _JWKS_CACHE and now < _JWKS_EXPIRY:
        return _JWKS_CACHE

    url = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                _JWKS_CACHE = resp.json()
                # Cache for 6 hours
                _JWKS_EXPIRY = now + (6 * 3600)
                return _JWKS_CACHE
    except Exception:
        pass
    return _JWKS_CACHE


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    x_dev_user_id: str | None = Header(default=None, alias="X-Dev-User-Id"),
) -> AuthenticatedUser:
    """
    Authenticate the request via Firebase ID token or Supabase JWT.
    Supports local dev bypass via X-Dev-User-Id header or mock token when in development/test.
    """
    # 1. Dev/Test bypass for rapid local development
    if settings.dev_login_enabled:
        if x_dev_user_id:
            return AuthenticatedUser(
                user_id=x_dev_user_id,
                email=f"{x_dev_user_id}@example.com",
                role="authenticated",
                claims={"sub": x_dev_user_id},
            )
        if not creds and not settings.firebase_client_email and not settings.supabase_url:
            return AuthenticatedUser(
                user_id="dev-user-001",
                email="dev@applyon.in",
                role="authenticated",
                claims={"sub": "dev-user-001"},
            )

    if not creds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTHENTICATION_REQUIRED",
                "message": "Missing bearer authentication token",
            },
        )

    token = creds.credentials

    # 2. Check for local dev token
    if settings.dev_login_enabled and token.startswith("dev-token-"):
        uid = token.replace("dev-token-", "")
        return AuthenticatedUser(
            user_id=uid,
            email=f"{uid}@example.com",
            role="authenticated",
            claims={"sub": uid},
        )

    # 3. Verify Firebase token using Google JWKS
    if settings.firebase_project_id:
        try:
            # First extract unverified header to get the key id (kid)
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            keys = await fetch_firebase_public_keys()
            if kid and kid in keys:
                # Google publishes X.509 certificates; PyJWT needs the public key inside them
                public_key = load_pem_x509_certificate(keys[kid].encode()).public_key()
                decoded = jwt.decode(
                    token,
                    public_key,  # type: ignore[arg-type]
                    algorithms=["RS256"],
                    audience=settings.firebase_project_id,
                    issuer=f"https://securetoken.google.com/{settings.firebase_project_id}",
                )
                user_id = decoded.get("user_id") or decoded.get("sub", "")
                return AuthenticatedUser(
                    user_id=user_id,
                    email=decoded.get("email"),
                    role="authenticated",
                    claims=decoded,
                )
        except Exception as e:
            # Try fallback to standard secret or Supabase
            logger.info("Firebase token rejected: %s", e)

    # 4. Fallback: Supabase / HS256 secret verification
    if settings.jwt_secret_key:
        try:
            decoded = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=["HS256"],
            )
            return AuthenticatedUser(
                user_id=decoded.get("sub", ""),
                email=decoded.get("email"),
                role=decoded.get("role", "authenticated"),
                claims=decoded,
            )
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "INVALID_TOKEN",
            "message": "The provided authentication token is invalid or expired",
        },
    )
