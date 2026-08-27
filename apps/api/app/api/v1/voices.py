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
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from vieneu_core import capabilities_for_runtime, probe_runtime

from app.config import settings
from app.database import get_async_session
from app.models.custom_voice import CustomVoiceModel
from app.models.omnivoice_voice import OmniVoiceVoiceModel
from app.models.tts_job import TTSJobModel
from app.schemas.custom_voice import (
    CustomVoiceListResponse,
    CustomVoiceResponse,
    VoiceAnalysisResponse,
    VoiceCapabilitiesResponse,
)
from app.schemas.omnivoice_voice import (
    OmniVoiceVoiceListResponse,
    OmniVoiceVoiceResponse,
)
from app.schemas.voice import VoiceListResponse, VoiceResponse
from app.services.plan_enforcement import check_request_feature
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
    request: Request = None,  # noqa: B008
) -> VoiceAnalysisResponse:
    """Analyze a reference locally and return a safe, path-free summary."""

    if not settings.voice_lab_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VOICE_LAB_DISABLED")
    check_request_feature(request, "voice_lab")
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
    provider_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=500, ge=1, le=1000),
):
    raw_voices = voice_catalog.list_voices(language=language)

    if provider_id:
        raw_voices = [
            voice for voice in raw_voices
            if voice.provider_id.casefold() == provider_id.casefold()
        ]

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
            gender=v.gender,
            region=v.region,
            style=v.style,
            description=v.description,
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
    denoise_mode: str = Form(default="auto"),
    clone_mode: str = Form(default="fidelity"),
    request: Request = None,  # noqa: B008
    session: AsyncSession = Depends(get_async_session)  # noqa: B008
):
    if not settings.voice_lab_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VOICE_LAB_DISABLED")
    check_request_feature(request, "voice_lab")
    check_request_feature(request, "custom_voices")
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

    # Reference transcript: normalize and enforce engine policy. V3 Turbo policy is
    # "optional" (stored as profile metadata, NOT used for enrollment); a future
    # transcript-conditioned engine may declare "required".
    normalized_transcript = transcript.strip()
    MAX_REFERENCE_TEXT_CHARS = 2000
    if len(normalized_transcript) > MAX_REFERENCE_TEXT_CHARS:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "REFERENCE_TEXT_TOO_LONG",
                "message": f"Reference transcript must be at most {MAX_REFERENCE_TEXT_CHARS} characters.",
            },
        )
    if (
        not normalized_transcript
        and getattr(clone_capabilities, "reference_text_policy", "optional") == "required"
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "REFERENCE_TEXT_REQUIRED",
                "message": "Reference transcript is required for this engine.",
            },
        )
    logger.debug(
        "voice clone reference_transcript_present=%s reference_transcript_chars=%d",
        bool(normalized_transcript),
        len(normalized_transcript),
    )

    temp_path = None

    try:
        temp_path = await save_upload_to_temp(
            audio_file,
            directory=settings.custom_voices_dir / ".uploads",
            max_bytes=settings.tts_audio_max_bytes,
        )
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
        reference_duration = (
            selection[1] - selection[0] if selection is not None else duration
        )

        analysis = None
        try:
            analysis = await analyze_audio_file_async(temp_path)
        except Exception as exc:
            logger.debug("Analysis calculation failed: %s", exc)

        entitlement = getattr(request.state, "entitlement", None)
        license_entitlement_id = entitlement.id if entitlement else None

        try:
            db_voice = await CloneOrchestrator().create(
                session=session,
                display_name=display_name,
                transcript=normalized_transcript,
                consent_given=consent_given,
                source_audio_path=temp_path,
                duration_seconds=reference_duration or 0.0,
                source_duration_seconds=duration or 0.0,
                reference_duration_seconds=reference_duration or 0.0,
                selected_start_seconds=selection[0] if selection else 0.0,
                selected_end_seconds=selection[1] if selection else duration,
                quality_score=analysis.quality_score if analysis else None,
                warnings=analysis.warnings if analysis else None,
                denoise_mode=denoise_mode,
                clone_mode=clone_mode,
                analysis=analysis,
                progress=lambda stage_name: logger.debug("Voice profile stage=%s", stage_name),
                license_entitlement_id=license_entitlement_id,
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

        return _serialize_custom_voice(db_voice)

    except VoiceAnalysisError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except Exception as exc:
        logger.exception("Voice profile persistence failed")
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save the voice profile. Please try again.",
        )
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _serialize_custom_voice(voice: CustomVoiceModel) -> CustomVoiceResponse:
    res = CustomVoiceResponse.model_validate(voice)
    calib_path = getattr(voice, "calibration_audio_path", None)
    res.calibration_available = bool(calib_path and Path(calib_path).is_file())
    return res


@router.get("/tts/voices/custom", response_model=CustomVoiceListResponse)
async def list_custom_voices(
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    include_omnivoice: bool = Query(default=True),
):
    """List VieNeu custom voices, optionally including OmniVoice designed voices."""
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

    items = [_serialize_custom_voice(v) for v in voices]

    if include_omnivoice:
        omni_filters = []
        if q and q.strip():
            omni_filters.append(OmniVoiceVoiceModel.display_name.ilike(f"%{q.strip()}%"))
        omni_stmt = (
            select(OmniVoiceVoiceModel)
            .where(*omni_filters)
            .order_by(OmniVoiceVoiceModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        omni_result = await session.execute(omni_stmt)
        omni_voices = omni_result.scalars().all()
        omni_total = await session.scalar(
            select(func.count(OmniVoiceVoiceModel.id)).where(*omni_filters)
        )
        items.extend([_serialize_omnivoice_voice(v) for v in omni_voices])
        total = (total or 0) + (omni_total or 0)

    return CustomVoiceListResponse(items=items, total=total or 0)


def _serialize_omnivoice_voice(voice: OmniVoiceVoiceModel) -> CustomVoiceResponse:
    """Render an OmniVoice designed voice in the custom-voice list shape.

    Uses an aliased response so the Voice Library can display it without
    creating a separate frontend card variant.
    """
    return CustomVoiceResponse.model_validate(
        {
            "id": voice.id,
            "display_name": voice.display_name,
            "transcript": voice.preview_text or "",
            "consent_given": True,
            "created_at": voice.created_at,
            "updated_at": voice.updated_at,
            "provider_id": voice.provider_id,
            "engine_id": voice.engine_id,
            "status": voice.status,
            "duration_seconds": None,
            "source_duration_seconds": None,
            "reference_duration_seconds": None,
            "selected_start_seconds": None,
            "selected_end_seconds": None,
            "quality_score": None,
            "consent_version": "omnivoice-design-v1",
            "profile_format_version": voice.prompt_format_version,
            "engine_version": voice.engine_version,
            "denoise_mode": "auto",
            "denoise_applied": False,
            "clone_mode": "fidelity",
            "speaker_similarity_score": None,
            "calibration_quality_score": None,
            "calibration_available": False,
        }
    )


@router.get("/tts/voices/custom/{voice_id}", response_model=CustomVoiceResponse)
async def get_custom_voice(
    voice_id: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    voice = await session.scalar(
        select(CustomVoiceModel).where(CustomVoiceModel.id == voice_id)
    )
    if voice:
        return _serialize_custom_voice(voice)

    omni = await session.scalar(
        select(OmniVoiceVoiceModel).where(OmniVoiceVoiceModel.id == voice_id)
    )
    if omni:
        return _serialize_omnivoice_voice(omni)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom voice not found.")


@router.get("/tts/voices/custom/{voice_id}/calibration/audio")
async def get_custom_voice_calibration_audio(
    voice_id: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    try:
        voice = await session.scalar(
            select(CustomVoiceModel).where(CustomVoiceModel.id == voice_id)
        )
        if not voice or not voice.calibration_audio_path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calibration audio not found.")
        calib_path = Path(voice.calibration_audio_path)
        if not calib_path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calibration audio file is missing.")
        return FileResponse(path=str(calib_path), media_type="audio/wav")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed serving calibration audio for voice %s", voice_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.delete("/tts/voices/custom/{voice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_voice(
    voice_id: str,
    session: AsyncSession = Depends(get_async_session)  # noqa: B008
):
    voice = await session.scalar(
        select(CustomVoiceModel).where(CustomVoiceModel.id == voice_id)
    )
    if voice:
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

        from app.services.voice_artifact_cleanup import delete_voice_profile_directory
        from app.services.voice_resolver import invalidate_voice_cache

        delete_voice_profile_directory(voice_id, settings.custom_voices_dir)
        invalidate_voice_cache(voice_id)

        await session.delete(voice)
        await session.commit()
        return

    # Allow deleting OmniVoice designed voices via the same custom-voice route.
    omni = await session.scalar(
        select(OmniVoiceVoiceModel).where(OmniVoiceVoiceModel.id == voice_id)
    )
    if omni:
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

        from app.services.voice_artifact_cleanup import delete_voice_profile_directory as delete_voice_dir
        from app.services.voice_resolver import invalidate_voice_cache

        delete_voice_dir(voice_id, settings.custom_voices_dir / "omnivoice")
        invalidate_voice_cache(voice_id)

        await session.delete(omni)
        await session.commit()
        return

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Custom voice not found."
    )


from vieneu_core.engine import ModelManager
from app.services.vieneu_resource_governor import vieneu_governor
from app.services.vieneu_runtime_warmup import warm_vieneu_background


@router.get("/tts/runtime/profile")
async def get_runtime_profile():
    """Return the active and persisted VieNeu hardware runtime execution profile."""
    profile = await vieneu_governor.initialize()
    return profile.to_dict()


@router.post("/tts/runtime/optimize")
async def optimize_runtime():
    """Run an automated local micro-benchmark to tune VieNeu for this machine."""
    manager = ModelManager()
    engine = await manager.get_engine()
    probe = probe_runtime()
    tuned = await vieneu_governor.reoptimize(
        engine=engine,
        device=probe.device,
        backend=probe.backend,
        mode=settings.vieneu_runtime_mode,
    )
    return tuned.to_dict()


@router.post("/tts/runtime/warmup")
async def warmup_runtime(voice_type: str | None = None):
    """Trigger background warmup for the VieNeu engine and selected voice artifact."""
    import asyncio
    asyncio.create_task(warm_vieneu_background(voice_type))
    return {"status": "warming"}
