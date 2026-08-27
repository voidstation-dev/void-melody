import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base
from app.models.license_entitlement import LicenseEntitlementModel
from app.models.license_plan import LicensePlanModel
from app.services.plan_enforcement import (
    PlanFeatureNotAllowedError,
    check_feature,
    check_provider_allowed,
    get_effective_features,
    is_feature_enabled,
    resolve_entitlement,
)


@pytest_asyncio.fixture
async def in_memory_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_session(in_memory_session):
    session = in_memory_session
    free = LicensePlanModel(
        slug="free",
        display_name="Free",
        is_active=True,
        priority=0,
        features={
            "tts": True,
            "voice_lab": False,
            "voice_design": False,
            "providers": ["capcut"],
            "max_custom_voices": 0,
        },
    )
    pro = LicensePlanModel(
        slug="pro",
        display_name="Pro",
        is_active=True,
        priority=10,
        features={
            "tts": True,
            "voice_lab": True,
            "voice_design": True,
            "providers": ["capcut", "vieneu", "omnivoice"],
            "max_custom_voices": 50,
        },
    )
    session.add_all([free, pro])
    await session.commit()
    return session


@pytest.mark.asyncio
async def test_dev_key_resolves_to_pro_plan(seeded_session):
    entitlement = await resolve_entitlement(seeded_session, "dev")
    assert entitlement is not None
    assert entitlement.plan.slug == "pro"


@pytest.mark.asyncio
async def test_unknown_key_resolves_to_default_plan(seeded_session):
    entitlement = await resolve_entitlement(seeded_session, "some-unknown-key")
    assert entitlement is not None
    assert entitlement.plan.slug == settings.default_plan_id


@pytest.mark.asyncio
async def test_free_plan_blocks_voice_lab_and_voice_design(seeded_session):
    entitlement = await resolve_entitlement(seeded_session, "")
    features = get_effective_features(entitlement)
    assert is_feature_enabled(features, "tts") is True
    assert is_feature_enabled(features, "voice_lab") is False
    with pytest.raises(PlanFeatureNotAllowedError):
        check_feature(features, "voice_lab")
    with pytest.raises(PlanFeatureNotAllowedError):
        check_feature(features, "voice_design")


@pytest.mark.asyncio
async def test_free_plan_allows_only_capcut(seeded_session):
    entitlement = await resolve_entitlement(seeded_session, "")
    features = get_effective_features(entitlement)
    check_provider_allowed(features, "capcut")
    with pytest.raises(PlanFeatureNotAllowedError):
        check_provider_allowed(features, "vieneu")
    with pytest.raises(PlanFeatureNotAllowedError):
        check_provider_allowed(features, "omnivoice")


@pytest.mark.asyncio
async def test_pro_plan_allows_all_features_and_providers(seeded_session):
    entitlement = await resolve_entitlement(seeded_session, "dev")
    features = get_effective_features(entitlement)
    check_feature(features, "tts")
    check_feature(features, "voice_lab")
    check_feature(features, "voice_design")
    check_provider_allowed(features, "capcut")
    check_provider_allowed(features, "vieneu")
    check_provider_allowed(features, "omnivoice")


@pytest.mark.asyncio
async def test_persistent_entitlement_lookup(seeded_session):
    pro = await seeded_session.scalar(select(LicensePlanModel).where(LicensePlanModel.slug == "pro"))
    entitlement = LicenseEntitlementModel(
        license_key="my-key-123",
        plan_id=pro.id,
        is_active=True,
    )
    seeded_session.add(entitlement)
    await seeded_session.commit()

    resolved = await resolve_entitlement(seeded_session, "my-key-123")
    assert resolved is not None
    assert resolved.license_key == "my-key-123"
    assert resolved.plan.slug == "pro"
