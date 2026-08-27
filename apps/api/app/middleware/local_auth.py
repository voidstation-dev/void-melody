import secrets

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings
from app.database import AsyncSessionLocal
from app.services.plan_enforcement import resolve_entitlement

PUBLIC_PATHS = {
    "/api/v1/health",
    "/api/v1/health/live",
}


def validate_runtime_security() -> None:
    if settings.app_env.lower() == "production" and not settings.melody_api_token:
        raise RuntimeError("MELODY_API_TOKEN is required when APP_ENV=production")


class LocalAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # Resolve license entitlement for every request so endpoints can enforce plan
        # limits. This runs before auth so dev/test environments without a token still
        # pick up the X-License-Key header and resolve to the right plan.
        license_key = request.headers.get("X-License-Key")
        if license_key:
            request.state.license_key = license_key
        try:
            async with AsyncSessionLocal() as session:
                entitlement = await resolve_entitlement(session, license_key)
                if entitlement is not None:
                    request.state.entitlement = entitlement
        except Exception:
            # Fail open for auth middleware; endpoints will fall back to default plan.
            pass

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
