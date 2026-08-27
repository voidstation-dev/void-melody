from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel

from app.database import get_async_session
from app.services.plan_enforcement import (
    PlanFeatureNotAllowedError,
    get_effective_features,
    resolve_entitlement,
)
from app.services.plan_enforcement import PlanFeatureNotAllowedError as PlanFeatureError

router = APIRouter(prefix="/license", tags=["License"])


class EntitlementResponse(BaseModel):
    entitlement_id: str | None
    license_key: str | None
    plan_id: str | None
    plan_slug: str | None
    plan_name: str | None
    is_active: bool
    features: dict | None
    error: str | None = None


class RefreshRequest(BaseModel):
    license_key: str | None = None


@router.get("/me", response_model=EntitlementResponse)
async def get_current_license(
    request: Request,
    x_license_key: str | None = Header(None, alias="X-License-Key"),
    session=Depends(get_async_session),
):
    """Return the resolved entitlement/features for the caller."""
    license_key = x_license_key or getattr(request.state, "license_key", None)
    entitlement = await resolve_entitlement(session, license_key)
    if entitlement is None:
        return EntitlementResponse(
            entitlement_id=None,
            license_key=license_key,
            plan_id=None,
            plan_slug=None,
            plan_name=None,
            is_active=False,
            features=None,
            error="No plan found for this license key.",
        )
    return EntitlementResponse(
        entitlement_id=entitlement.id,
        license_key=entitlement.license_key,
        plan_id=entitlement.plan_id,
        plan_slug=entitlement.plan.slug if entitlement.plan else None,
        plan_name=entitlement.plan.display_name if entitlement.plan else None,
        is_active=entitlement.is_active,
        features=get_effective_features(entitlement),
    )


@router.post("/refresh", response_model=EntitlementResponse)
async def refresh_license(
    request: Request,
    payload: RefreshRequest,
    x_license_key: str | None = Header(None, alias="X-License-Key"),
    session=Depends(get_async_session),
):
    """Resolve (or re-resolve) entitlement from a license key.

    This is a lightweight local lookup. A future billing integration could
    refresh from a remote license server here.
    """
    license_key = payload.license_key or x_license_key or getattr(request.state, "license_key", None)
    entitlement = await resolve_entitlement(session, license_key)
    if entitlement is None:
        return EntitlementResponse(
            entitlement_id=None,
            license_key=license_key,
            plan_id=None,
            plan_slug=None,
            plan_name=None,
            is_active=False,
            features=None,
            error="No plan found for this license key.",
        )
    return EntitlementResponse(
        entitlement_id=entitlement.id,
        license_key=entitlement.license_key,
        plan_id=entitlement.plan_id,
        plan_slug=entitlement.plan.slug if entitlement.plan else None,
        plan_name=entitlement.plan.display_name if entitlement.plan else None,
        is_active=entitlement.is_active,
        features=get_effective_features(entitlement),
    )
