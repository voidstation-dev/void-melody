from fastapi import APIRouter

from app.schemas.tts import TrialStatusResponse
from app.services.trial_service import get_runtime_trial_service

router = APIRouter()


@router.get("/trial/status", response_model=TrialStatusResponse)
async def get_trial_status() -> TrialStatusResponse:
    snapshot = get_runtime_trial_service().get_status()
    return TrialStatusResponse(
        status=snapshot.status.value,
        can_synthesize=snapshot.can_synthesize,
        first_run_at=snapshot.first_run_at,
        expires_at=snapshot.expires_at,
        remaining_seconds=snapshot.remaining_seconds,
        warning_level=snapshot.warning_level.value,
        override=snapshot.override,
    )
