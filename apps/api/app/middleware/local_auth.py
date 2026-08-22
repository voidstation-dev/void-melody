import secrets

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings
from app.services.license_context import (
    reset_runtime_license_key,
    set_runtime_license_key,
)

PUBLIC_PATHS = {
    "/api/v1/health",
    "/api/v1/health/live",
}


def validate_runtime_security() -> None:
    if settings.app_env.lower() == "production" and not settings.melody_api_token:
        raise RuntimeError("MELODY_API_TOKEN is required when APP_ENV=production")


class LocalAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        license_token = set_runtime_license_key(
            request.headers.get("X-Melody-License-Key")
        )
        try:
            if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
                return await call_next(request)

            expected = settings.melody_api_token
            if expected is None and settings.app_env.lower() != "production":
                return await call_next(request)

            supplied = request.headers.get("X-Melody-Token", "")
            if not expected or not secrets.compare_digest(supplied, expected):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "UNAUTHORIZED"},
                )
            return await call_next(request)
        finally:
            reset_runtime_license_key(license_token)
