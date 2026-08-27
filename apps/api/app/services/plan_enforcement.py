from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.license_entitlement import LicenseEntitlementModel
from app.models.license_plan import LicensePlanModel

logger = logging.getLogger(__name__)

DEFAULT_DEV_KEY = "dev"
DEFAULT_FEATURES = {
    "tts": True,
    "voice_lab": False,
    "voice_design": False,
    "audio_studio": False,
    "transcription": False,
    "runtime_install": False,
    "providers": ["capcut"],
    "max_custom_voices": 0,
    "max_concurrent_jobs": 1,
    "max_batch_files": 5,
}


class PlanFeatureNotAllowedError(Exception):
    """Raised when the active plan does not allow a feature or provider."""

    def __init__(self, feature: str, detail: str | None = None):
        self.feature = feature
        self.detail = detail or f"Feature '{feature}' is not included in your current plan."
        super().__init__(self.detail)

    def to_http_exception(self) -> HTTPException:
        return HTTPException(
            status_code=403,
            detail={
                "error_code": "PLAN_FEATURE_NOT_ALLOWED",
                "feature": self.feature,
                "message": self.detail,
            },
        )


async def resolve_entitlement(
    session: AsyncSession, license_key: str | None
) -> LicenseEntitlementModel | None:
    """Resolve the active entitlement for a license key.

    The dev key always resolves to the configured dev plan (default: pro).
    Anonymous or unknown keys fall back to the default plan (default: free).
    """
    plan_slug = _plan_slug_for_key(license_key)

    # Dev keys and fallback plans use deterministic synthetic entitlement rows
    # so downstream code can always dereference entitlement.plan.features.
    if not license_key or license_key.strip().lower() == DEFAULT_DEV_KEY:
        plan = await _get_plan_by_slug(session, plan_slug)
        if plan is None:
            logger.warning("Plan slug %r not found; using free fallback", plan_slug)
            plan = await _get_plan_by_slug(session, "free")
        if plan is None:
            return None
        return LicenseEntitlementModel(
            id=f"__{plan.slug}__",
            license_key=license_key or "",
            plan_id=plan.id,
            plan=plan,
            is_active=True,
        )

    stmt = (
        select(LicenseEntitlementModel)
        .where(
            LicenseEntitlementModel.license_key == license_key,
            LicenseEntitlementModel.is_active.is_(True),
        )
        .order_by(LicenseEntitlementModel.created_at.desc())
        .limit(1)
    )
    entitlement = await session.scalar(stmt)
    if entitlement is None:
        plan = await _get_plan_by_slug(session, plan_slug)
        if plan is None:
            return None
        return LicenseEntitlementModel(
            id=f"__{plan.slug}__",
            license_key=license_key,
            plan_id=plan.id,
            plan=plan,
            is_active=True,
        )
    return entitlement


def get_effective_features(entitlement: LicenseEntitlementModel | None) -> dict[str, Any]:
    """Return the merged feature dict for an entitlement."""
    if entitlement is None or entitlement.plan is None:
        return dict(DEFAULT_FEATURES)
    return dict(entitlement.plan.features or DEFAULT_FEATURES)


def is_feature_enabled(features: dict[str, Any], feature_name: str) -> bool:
    """Check whether a feature flag is enabled in the feature dict."""
    if not isinstance(features, dict):
        return False
    return bool(features.get(feature_name, False))


def check_feature(features: dict[str, Any], feature_name: str) -> None:
    """Raise PlanFeatureNotAllowedError if the feature is disabled."""
    if not is_feature_enabled(features, feature_name):
        raise PlanFeatureNotAllowedError(feature_name)


def check_provider_allowed(features: dict[str, Any], provider_id: str) -> None:
    """Raise PlanFeatureNotAllowedError if the provider is not allowed."""
    allowed = features.get("providers")
    if not isinstance(allowed, list):
        raise PlanFeatureNotAllowedError(
            "provider", detail="No providers are enabled for your current plan."
        )
    if provider_id not in allowed:
        raise PlanFeatureNotAllowedError(
            "provider",
            detail=f"Provider '{provider_id}' is not included in your current plan.",
        )


def get_request_features(request: Any) -> dict[str, Any]:
    """Convenience: read entitlement from request.state and return features."""
    entitlement = getattr(request.state, "entitlement", None) if request else None
    return get_effective_features(entitlement)


def check_request_feature(request: Any, feature_name: str) -> None:
    """Convenience: check a feature against request.state entitlement."""
    features = get_request_features(request)
    check_feature(features, feature_name)


def check_request_provider(request: Any, provider_id: str) -> None:
    """Convenience: check a provider against request.state entitlement."""
    features = get_request_features(request)
    check_provider_allowed(features, provider_id)


def _plan_slug_for_key(license_key: str | None) -> str:
    key = (license_key or "").strip().lower()
    if key == DEFAULT_DEV_KEY:
        return settings.dev_license_plan_id
    if key:
        # In a real billing integration we would map keys to plans server-side.
        # For now, unknown keys fall back to the default plan.
        return settings.default_plan_id
    return settings.default_plan_id


async def _get_plan_by_slug(session: AsyncSession, slug: str) -> LicensePlanModel | None:
    stmt = select(LicensePlanModel).where(
        LicensePlanModel.slug == slug,
        LicensePlanModel.is_active.is_(True),
    )
    return await session.scalar(stmt)
