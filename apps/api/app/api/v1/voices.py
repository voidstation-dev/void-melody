from dataclasses import asdict
from importlib.metadata import PackageNotFoundError, version
import logging
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from vieneu_core import capabilities_for_runtime, probe_runtime

from app.config import settings
from app.database import get_async_session
from app.models.custom_voice import CustomVoiceModel
from app.models.tts_job import TTSJobModel
from app.schemas.custom_voice import (
    CustomVoiceListResponse,
    CustomVoiceResponse,
    VoiceAnalysisResponse,
    VoiceCapabilitiesResponse,
)
from app.schemas.voice import VoiceListResponse, VoiceResponse
from app.services.voice_catalog import voice_catalog
from app.utils.audio_utils import get_audio_duration
from app.services.voice_analysis import (
    VoiceAnalysisError,
    analyze_audio_file_async,
    extract_reference_segment_async,
    normalized_extension,
    save_upload_to_temp,
    validate_reference_selection,
    MIN_REFERENCE_SECONDS,
)
from app.services.clone_orchestrator import CloneOrchestrationError, CloneOrchestrator
from app.services.clone_preflight import preflight_clone_reference

router = APIRouter()
logger = logging.getLogger(__name__)


def _vieneu_version() -> str | None:
    try:
        return version("vieneu")
    except PackageNotFoundError:
        return None


def _clone_runtime_capabilities():
    return capabilities_for_runtime(
        probe_runtime(), engine_version=_vieneu_version()
    )


@router.get("/tts/voices/capabilities", response_model=VoiceCapabilitiesResponse)
async def voice_capabilities() -> VoiceCapabilitiesResponse:
    """Report runtime truth without loading the VieNeu model."""

    if not settings.voice_lab_enabled:
        return VoiceCapabilitiesResponse(
            provider_id="vieneu",
            engine_id="v3turbo",
            engine_version=_vieneu_version(),
            runtime_available=False,
            device="unknown",
            backend="disabled",
            supports_preset_voices=True,
            supports_voice_cloning=False,
            supports_denoise=False,
            supports_streaming=False,
            reason_code="FEATURE_DISABLED",
            reason="Voice Lab is disabled by the app release flag.",
        )
    capabilities = capabilities_for_runtime(
        probe_runtime(), engine_version=_vieneu_version()
    )
    return VoiceCapabilitiesResponse(**asdict(capabilities))


@router.post("/tts/voices/analyze", response_model=VoiceAnalysisResponse)
async def analyze_voice_reference(
    audio_file: UploadFile = File(...),  # noqa: B008
) -> VoiceAnalysisResponse:
    """Analyze a reference locally and return a safe, path-free summary."""

    if not settings.voice_lab_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VOICE_LAB_DISABLED")
    if normalized_extension(audio_file.filename) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UNSUPPORTED_FORMAT", "message": "Choose a WAV, MP3, or M4A file."},
        )

    temp_path = None
    try:
        temp_path = await save_upload_to_temp(
            audio_file,
            directory=settings.custom_voices_dir / ".analysis",
            max_bytes=settings.tts_audio_max_bytes,
        )
        analysis = await analyze_audio_file_async(temp_path)
        return VoiceAnalysisResponse(**asdict(analysis))
    except VoiceAnalysisError as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@router.get("/voices", response_model=VoiceListResponse)
async def list_voices(
    language: str | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
):
    raw_voices = voice_catalog.list_voices(language=language)

    if q:
        query_str = q.lower()
        raw_voices = [
            v
            for v in raw_voices
            if query_str in v.display_name.lower() or query_str in v.voice_type.lower()
        ]

    total = len(raw_voices)
    start = (page - 1) * page_size
    items = [
        VoiceResponse(
            id=v.voice_type,
            languageCode=v.language_code,
            languageShort=v.language_short,
            voiceType=v.voice_type,
            displayName=v.display_name,
            resourceId=v.resource_id,
            capturedAt=v.captured_at,
            providerId=v.provider_id,
        )
        for v in raw_voices[start : start + page_size]
    ]

    return VoiceListResponse(items=items, page=page, pageSize=page_size, total=total)


@router.post("/tts/voices/clone", response_model=CustomVoiceResponse, status_code=status.HTTP_201_CREATED)
async def clone_voice(
    audio_file: UploadFile = File(...),  # noqa: B008
    transcript: str = Form(default=""),
    display_name: str = Form(...),
    consent_given: bool = Form(...),
    selected_start_seconds: float | None = Form(default=None),
    selected_end_seconds: float | None = Form(default=None),
    session: AsyncSession = Depends(get_async_session)  # noqa: B008
):
    if not settings.voice_lab_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VOICE_LAB_DISABLED")
    if not consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must provide consent to clone this voice."
        )

    extension = normalized_extension(audio_file.filename)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported audio format. Please upload .wav, .mp3, or .m4a."
        )

    clone_capabilities = _clone_runtime_capabilities()
    if not clone_capabilities.supports_voice_cloning:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "VOICE_CLONING_UNAVAILABLE",
                "reason_code": clone_capabilities.reason_code,
                "message": clone_capabilities.reason
                or "Voice cloning is unavailable on this installation.",
            },
        )

    temp_path = None
    segment_path = None
    final_path = None

    try:
        temp_path = await save_upload_to_temp(
            audio_file,
            directory=settings.custom_voices_dir / ".uploads",
            max_bytes=settings.tts_audio_max_bytes,
        )
        # Check duration
        duration = await get_audio_duration(temp_path)
        if duration is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio duration could not be determined.",
            )
        if duration < MIN_REFERENCE_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "TOO_SHORT",
                    "message": "Audio must be at least three seconds long.",
                },
            )
        selection = validate_reference_selection(
            selected_start_seconds,
            selected_end_seconds,
            duration_seconds=duration,
        )
        if duration > 8.0 and selection is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Audio clip is too long ({duration}s). Select a segment no longer than 8 seconds.",
            )

        settings.custom_voices_dir.mkdir(parents=True, exist_ok=True)
        voice_id = str(uuid.uuid4())
        reference_path = temp_path
        if selection is not None:
            segment_path = settings.custom_voices_dir / ".uploads" / f"{voice_id}.reference.wav"
            await extract_reference_segment_async(
                temp_path,
                segment_path,
                start_seconds=selection[0],
                end_seconds=selection[1],
            )
            reference_path = segment_path
        reference_duration = (
            selection[1] - selection[0] if selection is not None else duration
        )
        final_path = settings.custom_voices_dir / f"{voice_id}{'.wav' if segment_path else extension}"
        reference_path.replace(final_path)
        if reference_path == temp_path:
            temp_path = None
        else:
            segment_path = None
        try:
            db_voice = await CloneOrchestrator(preflight=preflight_clone_reference).create(
                session=session,
                display_name=display_name,
                transcript=transcript,
                consent_given=consent_given,
                reference_audio_path=final_path,
                duration_seconds=reference_duration or 0.0,
                source_duration_seconds=duration or 0.0,
                reference_duration_seconds=reference_duration or 0.0,
                selected_start_seconds=selection[0] if selection else 0.0,
                selected_end_seconds=selection[1] if selection else duration,
                progress=lambda stage_name: logger.debug("Voice profile stage=%s", stage_name),
            )
        except CloneOrchestrationError as exc:
            error_status = (
                status.HTTP_409_CONFLICT
                if exc.code == "DUPLICATE_NAME"
                else status.HTTP_503_SERVICE_UNAVAILABLE
                if exc.code.startswith("CLONE_") or exc.code == "REFERENCE_MISSING"
                else status.HTTP_400_BAD_REQUEST
            )
            raise HTTPException(
                status_code=error_status,
                detail={"code": exc.code, "message": exc.message},
            ) from exc

        return db_voice

    except VoiceAnalysisError as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        if segment_path is not None:
            segment_path.unlink(missing_ok=True)
        if final_path is not None and final_path.exists():
            final_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except Exception as exc:
        logger.exception("Voice profile persistence failed")
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        if segment_path is not None:
            segment_path.unlink(missing_ok=True)
        if final_path is not None and final_path.exists():
            final_path.unlink(missing_ok=True)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save the voice profile. Please try again.",
        )


@router.get("/tts/voices/custom", response_model=CustomVoiceListResponse)
async def list_custom_voices(
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    filters = []
    if q and q.strip():
        filters.append(CustomVoiceModel.display_name.ilike(f"%{q.strip()}%"))

    stmt = (
        select(CustomVoiceModel)
        .where(*filters)
        .order_by(CustomVoiceModel.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(stmt)
    voices = result.scalars().all()
    total = await session.scalar(
        select(func.count(CustomVoiceModel.id)).where(*filters)
    )

    return CustomVoiceListResponse(items=voices, total=total or 0)


@router.get("/tts/voices/custom/{voice_id}", response_model=CustomVoiceResponse)
async def get_custom_voice(
    voice_id: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    voice = await session.scalar(
        select(CustomVoiceModel).where(CustomVoiceModel.id == voice_id)
    )
    if not voice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom voice not found.")
    return voice


@router.delete("/tts/voices/custom/{voice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_voice(
    voice_id: str,
    session: AsyncSession = Depends(get_async_session)  # noqa: B008
):
    stmt = select(CustomVoiceModel).where(CustomVoiceModel.id == voice_id)
    result = await session.execute(stmt)
    voice = result.scalars().first()

    if not voice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom voice not found."
        )

    active_jobs = await session.scalar(
        select(func.count(TTSJobModel.id)).where(
            TTSJobModel.voice_type == voice_id,
            TTSJobModel.status.in_(["queued", "processing"]),
        )
    )
    if active_jobs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "VOICE_IN_USE",
                "message": "The voice cannot be deleted while a TTS job is queued or processing.",
            },
        )

    # Delete audio file
    if voice.reference_audio_path:
        Path(voice.reference_audio_path).unlink(missing_ok=True)

    await session.delete(voice)
    await session.commit()
