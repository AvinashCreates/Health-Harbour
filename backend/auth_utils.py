import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt

_DEVELOPMENT_SECRET = "dev-secret-change-in-production-please"
_KNOWN_DEVELOPMENT_SECRETS = {
    _DEVELOPMENT_SECRET,
    "local-development-secret-change-before-deployment-123456",
}
_APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
_CONFIGURED_SECRET = os.getenv("JWT_SECRET")
if _APP_ENV == "production" and (
    not _CONFIGURED_SECRET
    or not _CONFIGURED_SECRET.strip()
    or len(_CONFIGURED_SECRET) < 32
    or _CONFIGURED_SECRET in _KNOWN_DEVELOPMENT_SECRETS
):
    raise RuntimeError(
        "Production requires a unique JWT_SECRET of at least 32 characters"
    )

SECRET_KEY = _CONFIGURED_SECRET or _DEVELOPMENT_SECRET
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        claims = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require_exp": True, "require_sub": True},
        )
        if not isinstance(claims.get("sub"), str) or not claims["sub"].strip():
            return None
        return claims
    except JWTError:
        return None
