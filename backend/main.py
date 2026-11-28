import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import models  # noqa: F401  (registers models on Base before create_all)
from database import Base, DATABASE_URL, engine, get_db
from routers import audit, auth, care, clinical, consent, exchange, files, fhir, fhir_sync, registry
from services.fhir_server import FHIRIntegrationError, check_r4_server
from services.ledger import ledger_enabled, process_pending_events
from services.fhir_sync import process_fhir_sync

logger = logging.getLogger(__name__)

auto_create = os.getenv("DB_AUTO_CREATE")
if auto_create == "1" or (auto_create is None and DATABASE_URL.startswith("sqlite")):
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = None
    fhir_worker = None
    stop_worker = asyncio.Event()

    async def deliver_fhir_events():
        while not stop_worker.is_set():
            try:
                await asyncio.to_thread(process_fhir_sync, None, 20)
            except Exception:
                logger.exception("FHIR synchronization worker cycle failed")
            try:
                await asyncio.wait_for(stop_worker.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                pass

    async def deliver_ledger_events():
        while not stop_worker.is_set():
            try:
                await asyncio.to_thread(process_pending_events)
            except Exception:
                logger.exception("Fabric outbox delivery cycle failed")
            try:
                await asyncio.wait_for(stop_worker.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                pass

    fhir_worker = asyncio.create_task(deliver_fhir_events())
    if ledger_enabled():
        worker = asyncio.create_task(deliver_ledger_events())
    try:
        yield
    finally:
        stop_worker.set()
        if fhir_worker:
            await fhir_worker
        if worker:
            await worker


app = FastAPI(
    title="Consent-Aware FHIR + Blockchain Healthcare Exchange",
    version="0.1.0",
    description="Research prototype: FHIR R4 resource exchange between patients, "
                 "doctors and labs, gated by patient-granted, time-limited consent, "
                 "with a hash-chained audit trail.",
    lifespan=lifespan,
)

@app.exception_handler(FHIRIntegrationError)
async def fhir_integration_error_handler(request: Request, exc: FHIRIntegrationError):
    logger.warning(
        "FHIR integration request failed",
        extra={
            "http_method": request.method,
            "fhir_operation": exc.operation or "unspecified",
            "fhir_upstream_status": exc.upstream_status_code,
            "http_status": exc.status_code,
        },
    )
    detail = {
        409: "FHIR resource conflict",
        422: "FHIR request could not be processed",
    }.get(exc.status_code, "FHIR service is unavailable")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail},
    )

def _validate_production_configuration() -> None:
    if os.getenv("APP_ENV", "development").strip().lower() != "production":
        return

    database_url = DATABASE_URL.strip().lower()
    if not database_url.startswith("postgresql"):
        raise RuntimeError("Production requires a PostgreSQL DATABASE_URL")

    configured_origins = os.getenv(
        "CORS_ORIGINS",
        "",
    ).split(",")
    origins = [origin.strip() for origin in configured_origins if origin.strip()]
    if not origins or "*" in origins:
        raise RuntimeError("Production requires explicit CORS_ORIGINS without wildcards")
    from urllib.parse import urlsplit
    for origin in origins:
        parsed = urlsplit(origin)
        if parsed.scheme not in {"https"} or not parsed.hostname:
            raise RuntimeError("Production CORS origins must be HTTPS origins")
        if parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise RuntimeError("Production CORS origins must contain only scheme and host")
        hostname = parsed.hostname.lower()
        if hostname in {"localhost", "127.0.0.1", "::1"} or hostname.endswith(".localhost"):
            raise RuntimeError("Production CORS origins must not use loopback hosts")

    trusted_hosts = [
        host.strip()
        for host in os.getenv("TRUSTED_HOSTS", "").split(",")
        if host.strip()
    ]
    if not trusted_hosts or "*" in trusted_hosts:
        raise RuntimeError("Production requires explicit TRUSTED_HOSTS without wildcards")
    for host in trusted_hosts:
        if "://" in host or "/" in host or " " in host:
            raise RuntimeError("Production TRUSTED_HOSTS must contain hostnames only")
        hostname = host.lower().strip("[]")
        if hostname in {"localhost", "127.0.0.1", "::1"} or hostname.endswith(".localhost"):
            raise RuntimeError("Production TRUSTED_HOSTS must not use loopback hosts")

    if os.getenv("DOCUMENT_ENCRYPTION_REQUIRED", "false").strip().lower() != "true":
        raise RuntimeError("Production requires DOCUMENT_ENCRYPTION_REQUIRED=true")

    key = os.getenv("DOCUMENT_ENCRYPTION_KEY", "").strip()
    if not key:
        raise RuntimeError("Production requires DOCUMENT_ENCRYPTION_KEY")
    try:
        import base64
        if len(key) == 64:
            try:
                decoded = bytes.fromhex(key)
                if len(decoded) != 32:
                    raise ValueError
            except Exception:
                decoded = base64.b64decode(key, validate=True)
        else:
            decoded = base64.b64decode(key, validate=True)
    except Exception:
        try:
            decoded = bytes.fromhex(key)
        except Exception as exc:
            raise RuntimeError("DOCUMENT_ENCRYPTION_KEY must be base64 or hexadecimal") from exc
    if len(decoded) != 32:
        raise RuntimeError("DOCUMENT_ENCRYPTION_KEY must encode exactly 32 bytes")

    if os.getenv("DOCUMENT_SCAN_REQUIRED", "false").strip().lower() != "true":
        raise RuntimeError("Production requires DOCUMENT_SCAN_REQUIRED=true")
    if os.getenv("DOCUMENT_SCANNER", "unavailable").strip().lower() != "clamav":
        raise RuntimeError("Production requires the ClamAV document scanner")
    if not os.getenv("CLAMAV_HOST", "").strip():
        raise RuntimeError("Production requires CLAMAV_HOST")

    auth_provider = os.getenv("AUTH_PROVIDER", "local").strip().lower()
    if auth_provider == "local":
        raise RuntimeError("Production requires AUTH_PROVIDER=keycloak")
    if auth_provider == "keycloak":
        for name in ("KEYCLOAK_ISSUER", "KEYCLOAK_JWKS_URL", "KEYCLOAK_AUDIENCE"):
            if not os.getenv(name, "").strip():
                raise RuntimeError(f"Production requires {name}")

    fhir_mode = os.getenv("FHIR_MODE", "local").strip().lower()
    if fhir_mode == "hapi" and not os.getenv("FHIR_SERVER_URL", "").strip():
        raise RuntimeError("Production FHIR_MODE=hapi requires FHIR_SERVER_URL")

    if os.getenv("FABRIC_ENABLED", "false").strip().lower() == "true":
        ledger_enabled()


_validate_production_configuration()


allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173",
    ).split(",")
    if origin.strip()
]

trusted_hosts = [
    host.strip()
    for host in os.getenv(
        "TRUSTED_HOSTS",
        "localhost,127.0.0.1,testserver",
    ).split(",")
    if host.strip()
]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
)


@app.middleware("http")
async def apply_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


app.include_router(auth.router)
app.include_router(fhir.router)
app.include_router(consent.router)
app.include_router(files.router)
app.include_router(audit.router)
app.include_router(registry.router)
app.include_router(care.router)
app.include_router(fhir_sync.router)
app.include_router(exchange.router)
app.include_router(clinical.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "healthcare-exchange-backend"}


@app.get("/health/live")
def health_live():
    return {"status": "alive", "service": "healthharbor-backend"}


@app.get("/health/ready")
def readiness(db: Session = Depends(get_db)):
    components = {"database": False, "fhir": True, "scanner": True, "encryption": True, "fabric": True}
    try:
        db.execute(text("SELECT 1"))
        components["database"] = True
    except SQLAlchemyError:
        pass

    if os.getenv("FHIR_MODE", "local").strip().lower() == "hapi":
        try:
            check_r4_server()
        except FHIRIntegrationError:
            components["fhir"] = False

    if os.getenv("DOCUMENT_ENCRYPTION_REQUIRED", "false").strip().lower() == "true":
        try:
            key = os.getenv("DOCUMENT_ENCRYPTION_KEY", "").strip()
            if not key:
                components["encryption"] = False
            else:
                try:
                    import base64
                    decoded = base64.b64decode(key, validate=True)
                except Exception:
                    try:
                        decoded = bytes.fromhex(key)
                    except Exception:
                        components["encryption"] = False
                        decoded = b""
                if len(decoded) != 32:
                    components["encryption"] = False
        except Exception:
            components["encryption"] = False

    if os.getenv("DOCUMENT_SCAN_REQUIRED", "false").strip().lower() == "true":
        scanner = os.getenv("DOCUMENT_SCANNER", "unavailable").strip().lower()
        if scanner == "clamav" and os.getenv("CLAMAV_HOST", "").strip():
            from services.document_scanner import scanner_is_reachable
            components["scanner"] = scanner_is_reachable()
        else:
            components["scanner"] = False

    if os.getenv("FABRIC_ENABLED", "false").strip().lower() == "true":
        try:
            components["fabric"] = ledger_enabled()
        except Exception:
            components["fabric"] = False

    ready = all(components.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "degraded", "components": components},
    )


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database readiness check failed",
        ) from exc
    services = {"database": "connected"}
    try:
        services["fhir"] = check_r4_server().get("mode", "local")
    except FHIRIntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FHIR server readiness check failed",
        ) from exc
    return {"status": "healthy", "services": services}
