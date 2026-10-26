"""Firebase ID tokens are verified against Google's X.509 certificates."""

import datetime as dt

import jwt
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from apps.api.deps import auth

PROJECT = "applyon-test"


def _cert_and_key() -> tuple[str, rsa.RSAPrivateKey]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "securetoken")])
    now = dt.datetime.now(dt.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode(), key


def _token(key: rsa.RSAPrivateKey, audience: str = PROJECT) -> str:
    now = dt.datetime.now(dt.UTC)
    claims = {
        "iss": f"https://securetoken.google.com/{PROJECT}",
        "aud": audience,
        "sub": "uid-123",
        "user_id": "uid-123",
        "email": "priya@example.com",
        "iat": now,
        "exp": now + dt.timedelta(hours=1),
    }
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "k1"})


@pytest.fixture
def firebase(monkeypatch: pytest.MonkeyPatch) -> rsa.RSAPrivateKey:
    cert, key = _cert_and_key()

    async def keys() -> dict[str, str]:
        return {"k1": cert}

    monkeypatch.setattr(auth, "fetch_firebase_public_keys", keys)
    monkeypatch.setattr(auth.settings, "firebase_project_id", PROJECT)
    monkeypatch.setattr(auth.settings, "app_env", "production")
    monkeypatch.setattr(auth.settings, "allow_dev_login", False)
    return key


@pytest.mark.asyncio
async def test_valid_firebase_token_is_accepted(firebase: rsa.RSAPrivateKey) -> None:
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=_token(firebase))
    user = await auth.get_current_user(creds, None)
    assert (user.user_id, user.email) == ("uid-123", "priya@example.com")


@pytest.mark.asyncio
async def test_token_for_another_project_is_rejected(firebase: rsa.RSAPrivateKey) -> None:
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=_token(firebase, audience="other"))
    with pytest.raises(HTTPException) as e:
        await auth.get_current_user(creds, None)
    assert e.value.status_code == 401
