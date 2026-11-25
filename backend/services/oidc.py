import os
import threading
import time
from typing import Any

import httpx
from jose import jwk, jwt
from jose.exceptions import JWTError


class OIDCConfigurationError(RuntimeError):
    pass


_JWKS: dict[str, Any] | None = None
_JWKS_EXPIRES = 0.0
_JWKS_URL: str | None = None
_JWKS_LOCK = threading.Lock()
_JWKS_TTL_SECONDS = 300


def oidc_settings() -> dict[str, str]:
    issuer = os.getenv("KEYCLOAK_ISSUER", "").rstrip("/")
    jwks_url = os.getenv("KEYCLOAK_JWKS_URL", "")
    audience = os.getenv("KEYCLOAK_AUDIENCE", "")
    if not issuer or not jwks_url or not audience:
        raise OIDCConfigurationError(
            "Keycloak mode requires KEYCLOAK_ISSUER, KEYCLOAK_JWKS_URL, and KEYCLOAK_AUDIENCE"
        )
    return {"issuer": issuer, "jwks_url": jwks_url, "audience": audience}


def _load_jwks(jwks_url: str, force: bool = False) -> dict[str, Any]:
    global _JWKS, _JWKS_EXPIRES, _JWKS_URL
    with _JWKS_LOCK:
        if (
            _JWKS is not None
            and _JWKS_URL == jwks_url
            and _JWKS_EXPIRES > time.monotonic()
            and not force
        ):
            return _JWKS
        try:
            response = httpx.get(jwks_url, timeout=5.0)
            response.raise_for_status()
            keys = response.json().get("keys")
        except (httpx.HTTPError, ValueError) as exc:
            raise OIDCConfigurationError("Unable to retrieve Keycloak signing keys") from exc
        if not isinstance(keys, list):
            raise OIDCConfigurationError("Keycloak JWKS response has no keys array")
        _JWKS = {"keys": keys}
        _JWKS_EXPIRES = time.monotonic() + _JWKS_TTL_SECONDS
        _JWKS_URL = jwks_url
        return _JWKS


def decode_keycloak_token(token: str) -> dict[str, Any]:
    settings = oidc_settings()
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        raise
    if header.get("alg") != "RS256" or not header.get("kid"):
        raise JWTError("Unsupported Keycloak token signing algorithm")

    jwks = _load_jwks(settings["jwks_url"])
    matching = next((key for key in jwks["keys"] if key.get("kid") == header["kid"]), None)
    if matching is None:
        jwks = _load_jwks(settings["jwks_url"], force=True)
        matching = next((key for key in jwks["keys"] if key.get("kid") == header["kid"]), None)
    if matching is None:
        raise JWTError("No matching Keycloak signing key")

    signing_key = jwk.construct(matching, algorithm="RS256")
    claims = jwt.decode(
        token,
        signing_key,
        algorithms=["RS256"],
        issuer=settings["issuer"],
        audience=settings["audience"],
        options={"require_exp": True, "require_iss": True, "require_sub": True},
    )
    audience = claims.get("aud")
    if not (
        audience == settings["audience"]
        or (
            isinstance(audience, list)
            and settings["audience"] in audience
        )
    ):
        raise JWTError("Token audience is missing or invalid")
    if not isinstance(claims.get("sub"), str) or not claims["sub"].strip():
        raise JWTError("Token subject is missing or invalid")
    return claims


def map_keycloak_role(claims: dict[str, Any]) -> str | None:
    role_map = {
        "PATIENT": "patient",
        "PHYSICIAN": "doctor",
        "LAB": "lab",
        "LAB_TECHNICIAN": "lab_technician",
        "LAB_SUPERVISOR": "lab_supervisor",
        "ADMIN": "admin",
    }
    realm_access = claims.get("realm_access", {})
    realm_roles = realm_access.get("roles", []) if isinstance(realm_access, dict) else []
    if not isinstance(realm_roles, list):
        return None
    mapped_roles = {
        role_map[candidate]
        for candidate in realm_roles
        if isinstance(candidate, str) and candidate in role_map
    }
    return next(iter(mapped_roles)) if len(mapped_roles) == 1 else None


def reset_jwks_cache() -> None:
    global _JWKS, _JWKS_EXPIRES, _JWKS_URL
    with _JWKS_LOCK:
        _JWKS = None
        _JWKS_EXPIRES = 0.0
        _JWKS_URL = None
