import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import models  # noqa: F401  (registers models on Base before create_all)
from database import Base, DATABASE_URL, engine, get_db
from routers import audit, auth, care, consent, exchange, files, fhir, fhir_sync, registry
from services.fhir_server import FHIRIntegrationError, check_r4_server
from services.ledger import ledger_enabled, process_pending_events

logger = logging.getLogger(__name__)

auto_create = os.getenv("DB_AUTO_CREATE")
if auto_create == "1" or (auto_create is None and DATABASE_URL.startswith("sqlite")):
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = None
    stop_worker = asyncio.Event()

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

    if ledger_enabled():
        worker = asyncio.create_task(deliver_ledger_events())
    try:
        yield
    finally:
        stop_worker.set()
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

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173",
    ).split(",")
    if origin.strip()
]

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


@app.get("/")
def root():
    return {"status": "ok", "service": "healthcare-exchange-backend"}


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
