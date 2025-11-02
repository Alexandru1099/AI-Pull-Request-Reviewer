import logging
import time
import uuid
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.core.config import get_settings

settings = get_settings()

logger = logging.getLogger("repo_aware")

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Backend API for Repo-Aware AI Pull Request Reviewer. "
        "Production-minded, with structured logging and safe defaults."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.allow_origins],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def add_request_id_and_logging(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    start = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled error during request",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
            },
        )
        response = JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Unexpected server error. Please try again later.",
                    "request_id": request_id,
                }
            },
        )

    elapsed = time.monotonic() - start
    logger.info(
        "HTTP request completed",
        extra={
          "request_id": request_id,
          "path": request.url.path,
          "method": request.method,
          "status_code": response.status_code,
          "elapsed_ms": int(elapsed * 1000),
        },
    )
    response.headers["x-request-id"] = request_id
    return response


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    logger.exception(
        "Unhandled exception",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "Unexpected server error. Please try again later.",
                "request_id": request_id,
            }
        },
    )


app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def root() -> Dict[str, Any]:
    return {
        "message": "Repo-Aware AI Pull Request Reviewer backend is running.",
    }
