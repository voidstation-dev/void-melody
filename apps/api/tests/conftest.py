import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.license_entitlement import LicenseEntitlementModel
from app.models.license_plan import LicensePlanModel


PRO_PLAN_FEATURES = {
    "tts": True,
    "voice_lab": True,
    "custom_voices": True,
    "voice_design": True,
    "audio_studio": True,
    "transcription": True,
    "runtime_install": True,
    "providers": ["capcut", "vieneu", "omnivoice"],
    "max_custom_voices": 50,
    "max_concurrent_jobs": 5,
    "max_batch_files": 50,
}


def make_pro_plan() -> LicensePlanModel:
    """Return a synthetic pro plan for use in tests."""
    return LicensePlanModel(
        id="__pro__",
        slug="pro",
        display_name="Pro",
        is_active=True,
        priority=10,
        features=PRO_PLAN_FEATURES,
    )


def make_pro_entitlement() -> LicenseEntitlementModel:
    """Return a synthetic pro entitlement for use in tests."""
    plan = make_pro_plan()
    return LicenseEntitlementModel(
        id="__pro_test__",
        license_key="dev",
        plan_id=plan.id,
        plan=plan,
        is_active=True,
    )


def make_fake_request(entitlement: LicenseEntitlementModel | None = None):
    """Return a minimal fake request carrying the given entitlement.

    Defaults to a synthetic pro entitlement so tests can exercise all
    providers and features without hitting the database.
    """
    if entitlement is None:
        entitlement = make_pro_entitlement()

    class FakeRequest:
        def __init__(self, entitlement):
            self.state = type("State", (), {"entitlement": entitlement})()

    return FakeRequest(entitlement)


@pytest_asyncio.fixture
async def async_session_factory(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    try:
        yield session_factory
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def async_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with SessionLocal() as session:
        yield session
    await engine.dispose()
