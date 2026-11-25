import os

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose.exceptions import JWTError
from sqlalchemy.orm import Session

import models
from auth_utils import decode_access_token
from database import get_db
from services.oidc import OIDCConfigurationError, decode_keycloak_token, map_keycloak_role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def verify_keycloak_claims(token: str) -> dict:
    try:
        return decode_keycloak_token(token)
    except OIDCConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Identity provider verification is unavailable",
        ) from exc
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if os.getenv("AUTH_PROVIDER", "local").lower() == "keycloak":
        payload = verify_keycloak_claims(token)
        subject = payload.get("sub")
        user = db.query(models.User).filter(models.User.identity_subject == subject).first()
        token_role = map_keycloak_role(payload)
        if user is None or token_role is None or user.role != token_role:
            raise credentials_exception
        return user

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


def require_roles(*roles: str):
    def checker(current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail=f"Requires role(s): {', '.join(roles)}")
        return current_user
    return checker
