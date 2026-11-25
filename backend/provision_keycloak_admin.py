import argparse
import os
import secrets

import models
from auth_utils import hash_password
from database import SessionLocal
from services import audit_logger


def main() -> None:
    if os.getenv("AUTH_PROVIDER", "").lower() != "keycloak":
        raise SystemExit("Set AUTH_PROVIDER=keycloak before creating an OIDC administrator profile")

    parser = argparse.ArgumentParser(description="Provision the first Keycloak-backed application administrator.")
    parser.add_argument("--subject", required=True, help="Keycloak user ID (sub) copied from the trusted admin console")
    parser.add_argument("--email", required=True, help="Email address from that Keycloak account")
    parser.add_argument("--name", required=True, help="Display name from that Keycloak account")
    args = parser.parse_args()
    if len(args.name.strip()) < 2:
        raise SystemExit("--name must contain at least two characters")

    db = SessionLocal()
    try:
        if db.query(models.User).filter(
            (models.User.identity_subject == args.subject) | (models.User.email == args.email)
        ).first():
            raise SystemExit("A profile with this subject or email already exists; refusing to link accounts")
        user = models.User(
            full_name=args.name.strip(),
            email=args.email,
            hashed_password=hash_password(secrets.token_urlsafe(48)),
            role="admin",
            identity_subject=args.subject,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        audit_logger.log_event(db, user.id, "USER_PROVISIONED", {
            "role": "admin",
            "provisioning_method": "operator_cli",
        })
        print(f"Keycloak administrator profile created for {user.email}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
