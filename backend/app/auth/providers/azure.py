"""Microsoft Entra ID (Azure AD) access token validation."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt
from jose.utils import base64url_decode

from app.core.config import Settings, settings

logger = logging.getLogger(__name__)

JWKS_CACHE_TTL_SECONDS = 3600

_jwks_cache: dict[str, Any] | None = None
_jwks_cache_fetched_at: float = 0.0


@dataclass(frozen=True)
class AzureTokenClaims:
    oid: str
    email: str
    name: str
    preferred_username: str | None = None


def clear_jwks_cache() -> None:
    """Reset cached JWKS (for tests)."""
    global _jwks_cache, _jwks_cache_fetched_at
    _jwks_cache = None
    _jwks_cache_fetched_at = 0.0


def _ensure_azure_configured(config: Settings) -> tuple[str, str, str, str]:
    """Return (issuer, jwks_url, client_id, tenant_id)."""
    issuer = config.effective_azure_issuer
    jwks_url = config.effective_azure_jwks_url
    client_id = config.azure_api_client_id
    tenant_id = config.azure_tenant_id
    if not issuer or not jwks_url or not client_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Azure authentication is not configured",
        )
    return issuer, jwks_url, client_id, tenant_id


def _valid_audiences(client_id: str) -> set[str]:
    return {client_id, f"api://{client_id}"}


def _valid_issuers(tenant_id: str) -> set[str]:
    """Accept both Azure AD v1 and v2 token issuers for the same tenant."""
    return {
        f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        f"https://sts.windows.net/{tenant_id}/",
    }


def _fetch_jwks(jwks_url: str) -> dict[str, Any]:
    global _jwks_cache, _jwks_cache_fetched_at
    now = time.time()
    if _jwks_cache is not None and now - _jwks_cache_fetched_at < JWKS_CACHE_TTL_SECONDS:
        return _jwks_cache

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(jwks_url)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch Azure JWKS from %s: %s", jwks_url, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify authentication token",
        ) from exc

    if not isinstance(payload, dict) or not payload.get("keys"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify authentication token",
        )

    _jwks_cache = payload
    _jwks_cache_fetched_at = now
    return payload


def _find_jwk(jwks: dict[str, Any], kid: str | None) -> dict[str, Any] | None:
    for key in jwks.get("keys", []):
        if isinstance(key, dict) and key.get("kid") == kid:
            return key
    return None


def _rsa_public_key_from_jwk(jwk_dict: dict[str, Any]) -> str:
    """Build PEM public key from JWK n/e fields for python-jose."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    n = int.from_bytes(base64url_decode(jwk_dict["n"].encode("utf-8")), byteorder="big")
    e = int.from_bytes(base64url_decode(jwk_dict["e"].encode("utf-8")), byteorder="big")
    public_key = rsa.RSAPublicNumbers(e, n).public_key()
    return public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode("utf-8")


def _looks_like_id_token(claims: dict[str, Any]) -> bool:
    if claims.get("token_use") == "id":
        return True
    # ID tokens often carry nonce; API access tokens use scp/roles instead.
    if claims.get("nonce") and not claims.get("scp") and not claims.get("roles"):
        return True
    return False


def _identity_email_from_claims(claims: dict[str, Any]) -> str | None:
    for key in ("preferred_username", "email", "upn"):
        value = claims.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return None


def _name_from_claims(claims: dict[str, Any], email: str) -> str:
    name = claims.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return email


def validate_azure_access_token(token: str, config: Settings | None = None) -> AzureTokenClaims:
    """Validate a Microsoft Entra access token and return normalized claims."""
    config = config or settings
    issuer, jwks_url, client_id, tenant_id = _ensure_azure_configured(config)

    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    jwk_dict = _find_jwk(_fetch_jwks(jwks_url), header.get("kid"))
    if jwk_dict is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        public_key = _rsa_public_key_from_jwk(jwk_dict)
        # Log unverified claims to aid debugging
        try:
            unverified = jwt.get_unverified_claims(token)
            logger.info(
                "Token claims (unverified): iss=%s aud=%s exp=%s scp=%s",
                unverified.get("iss"), unverified.get("aud"),
                unverified.get("exp"), unverified.get("scp"),
            )
            logger.info("Expected issuers=%s aud_set=%s", _valid_issuers(tenant_id), _valid_audiences(client_id))
        except Exception as _dbg_exc:
            logger.warning("Could not decode token for debug logging: %s", _dbg_exc)

        # python-jose requires audience to be a single string; skip built-in aud/iss
        # verification and check them manually so we can accept multiple valid values.
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False, "verify_exp": True, "verify_iss": False},
        )
    except JWTError as exc:
        logger.warning("JWT decode failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if not isinstance(claims, dict):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Manual issuer check — accept both v1 and v2 Azure issuers for the tenant
    token_iss = claims.get("iss", "")
    if token_iss not in _valid_issuers(tenant_id):
        logger.warning("Issuer rejected: %s", token_iss)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Manual audience check — accept bare client ID or api:// prefixed form
    token_aud = claims.get("aud")
    valid_auds = _valid_audiences(client_id)
    if isinstance(token_aud, list):
        if not any(a in valid_auds for a in token_aud):
            logger.warning("Audience rejected (list): %s", token_aud)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    elif token_aud not in valid_auds:
        logger.warning("Audience rejected: %s", token_aud)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if _looks_like_id_token(claims):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID tokens are not accepted; use an access token",
        )

    oid = claims.get("oid") or claims.get("sub")
    if not isinstance(oid, str) or not oid.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    email = _identity_email_from_claims(claims)
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    preferred_username = claims.get("preferred_username")
    return AzureTokenClaims(
        oid=oid.strip(),
        email=email,
        name=_name_from_claims(claims, email),
        preferred_username=preferred_username.strip() if isinstance(preferred_username, str) else None,
    )
