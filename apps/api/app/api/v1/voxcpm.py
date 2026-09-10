"""VoxCPM2 provider API endpoints.

Provider isolation rule: this router never calls VieneuProvider or reuses
tts_custom_voices. A VoxCPM2 clone is a reference-audio identity asset stored
in its own table (tts_voxcpm_voices) and its own storage subdirectory.
"""

from __future__ import annotations

import logging
import uuid
import wave
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
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_async_session
from app.db.repositories.voxcpm_voices import VoxCpmVoiceRepository
from app.models.voxcpm_voice import VoxCpmVoiceModel
from app.schemas.voxcpm_voice import (
    VoxCpmGenerateRequest,
    VoxCpmGenerateResponse,
    VoxCpmReferenceAnalysisResponse,
    VoxCpmVoiceListResponse,
    VoxCpmVoiceResponse,
)
from app.services.voice_analysis import (
    VoiceAnalysisError,
    analyze_audio_file_async,
    extract_reference_segment_async,
    normalized_extension,
    save_upload_to_temp,
    validate_reference_selection,
)

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_REFERENCE_TEXT_CHARS = 2000


def _voxcpm_storage_dir() -> Path:
    return settings.custom_voices_dir / "voxcpm2"


def _read_wav_properties(path: Path) -> tuple[float, int, int]:
    try:
        with wave.open(str(path), "rb") as source:
            sample_rate = source.getframerate()
            channels = source.getnchannels()
            duration = source.getnframes() / sample_rate if sample_rate > 0 else 0.0
    except (OSError, wave.Error):
        return 0.0, 0, 0
    return round(duration, 3), sample_rate, channels


@router.post("/voxcpm/voices/analyze", response_model=VoxCpmReferenceAnalysisResponse)
async def analyze_voxcpm_reference(
    audio_file: UploadFile = File(...),  # noqa: B008
) -> VoxCpmReferenceAnalysisResponse:
    """Analyze a VoxCPM2 reference audio locally; returns a path-free summary."""
    if normalized_extension(audio_file.filename) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UNSUPPORTED_FORMAT", "message": "Choose a WAV, MP3, or M4A file."},
        )

    temp_path = None
    try:
        temp_path = await save_upload_to_temp(
            audio_file,
            directory=settings.custom_voices_dir / "voxcpm2" / ".analysis",
            max_bytes=settings.tts_audio_max_bytes,
        )
        analysis = await analyze_audio_file_async(temp_path)
        return VoxCpmReferenceAnalysisResponse(
            duration_seconds=analysis.duration_seconds,
            source_duration_seconds=analysis.source_duration_seconds or analysis.duration_seconds,
            selected_start_seconds=analysis.selected_start_seconds,
            selected_end_seconds=analysis.selected_end_seconds,
            reference_duration_seconds=analysis.reference_duration_seconds
            or (analysis.selected_end_seconds - analysis.selected_start_seconds),
            speech_ratio=analysis.speech_ratio,
            noise_level_db=analysis.noise_level_db,
            clipping_ratio=analysis.clipping_ratio,
            quality_score=analysis.quality_score,
            waveform_peaks=analysis.waveform_peaks,
            warnings=analysis.warnings,
            recommended_start_seconds=analysis.recommended_start_seconds,
            recommended_end_seconds=analysis.recommended_end_seconds,
            metrics=analysis.metrics,
        )
    except VoiceAnalysisError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@router.post("/voxcpm/voices", response_model=VoxCpmVoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_voxcpm_voice(
    audio_file: UploadFile = File(...),  # noqa: B008
    display_name: str = Form(...),
    consent_given: bool = Form(...),
    description: str = Form(default=""),
    reference_transcript: str = Form(default=""),
    selected_start_seconds: float | None = Form(default=None),
    selected_end_seconds: float | None = Form(default=None),
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> VoxCpmVoiceResponse:
    """Create a VoxCPM2 clone profile from uploaded reference audio.

    The canonical normalized reference WAV is the profile; no enrollment
    embedding is computed (unlike VieNeu custom voices).
    """
    if not consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must provide consent to clone this voice.",
        )

    display_name_clean = display_name.strip()
    if not display_name_clean:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "NAME_REQUIRED", "message": "Voice name is required."},
        )
    if len(display_name_clean) > 255:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "NAME_TOO_LONG", "message": "Voice name must be at most 255 characters."},
        )

    normalized_transcript = (reference_transcript or "").strip()
    if len(normalized_transcript) > MAX_REFERENCE_TEXT_CHARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "REFERENCE_TEXT_TOO_LONG",
                "message": f"Reference transcript must be at most {MAX_REFERENCE_TEXT_CHARS} characters.",
            },
        )

    extension = normalized_extension(audio_file.filename)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported audio format. Please upload .wav, .mp3, or .m4a.",
        )

    repository = VoxCpmVoiceRepository(session)
    existing = await repository.list_voices(q=display_name_clean)
    if any(v.display_name.casefold() == display_name_clean.casefold() for v in existing):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DUPLICATE_NAME", "message": "A voice with this name already exists."},
        )

    temp_path = None
    try:
        temp_path = await save_upload_to_temp(
            audio_file,
            directory=_voxcpm_storage_dir() / ".uploads",
            max_bytes=settings.tts_audio_max_bytes,
        )

        # Full-source analysis (also enforces the >= 3s minimum).
        analysis = await analyze_audio_file_async(temp_path)
        duration = analysis.duration_seconds

        selection = validate_reference_selection(
            selected_start_seconds,
            selected_end_seconds,
            duration_seconds=duration,
        )

        source_duration = analysis.source_duration_seconds or duration
        if source_duration > 8.0 and selection is None:
            # Auto-adopt the recommended segment instead of failing: VoxCPM2
            # works from a bounded reference window chosen by the analyzer.
            selection = (
                analysis.recommended_start_seconds or analysis.selected_start_seconds,
                analysis.recommended_end_seconds or analysis.selected_end_seconds,
            )

        start, end = selection if selection is not None else (
            analysis.selected_start_seconds,
            analysis.selected_end_seconds,
        )

        storage_dir = _voxcpm_storage_dir()
        storage_dir.mkdir(parents=True, exist_ok=True)
        reference_path = storage_dir / f"{uuid.uuid4().hex}.wav"
        await extract_reference_segment_async(
            temp_path,
            reference_path,
            start_seconds=start,
            end_seconds=end,
        )

        ref_duration, ref_sample_rate, ref_channels = _read_wav_properties(reference_path)
        reference_duration = (end - start) if selection is not None else (
            analysis.selected_end_seconds - analysis.selected_start_seconds
        )

        db_voice = VoxCpmVoiceModel(
            display_name=display_name_clean,
            description=(description or "").strip() or None,
            reference_audio_path=str(reference_path),
            reference_original_filename=audio_file.filename,
            reference_duration_seconds=round(reference_duration, 3),
            reference_sample_rate=ref_sample_rate,
            reference_channels=ref_channels,
            reference_transcript=normalized_transcript or None,
            quality_score=analysis.quality_score,
            speech_ratio=analysis.speech_ratio,
            noise_level_db=analysis.noise_level_db,
            clipping_ratio=analysis.clipping_ratio,
        )
        db_voice = await repository.save(db_voice)
        return VoxCpmVoiceResponse.model_validate(db_voice)

    except VoiceAnalysisError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("VoxCPM2 voice persistence failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save the VoxCPM2 voice. Please try again.",
        ) from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@router.get("/voxcpm/voices", response_model=VoxCpmVoiceListResponse)
async def list_voxcpm_voices(
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> VoxCpmVoiceListResponse:
    repository = VoxCpmVoiceRepository(session)
    voices = await repository.list_voices(
        status=status_filter,
        q=q,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    total = getattr(repository, "last_total", None) or 0
    return VoxCpmVoiceListResponse(
        items=[VoxCpmVoiceResponse.model_validate(v) for v in voices],
        total=total,
    )


@router.get("/voxcpm/voices/{voice_id}", response_model=VoxCpmVoiceResponse)
async def get_voxcpm_voice(
    voice_id: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> VoxCpmVoiceResponse:
    repository = VoxCpmVoiceRepository(session)
    voice = await repository.get_by_id(voice_id)
    if not voice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VoxCPM2 voice not found.",
        )
    return VoxCpmVoiceResponse.model_validate(voice)


@router.delete("/voxcpm/voices/{voice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voxcpm_voice(
    voice_id: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> None:
    repository = VoxCpmVoiceRepository(session)
    voice = await repository.get_by_id(voice_id)
    if not voice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VoxCPM2 voice not found.",
        )

    reference_path = Path(voice.reference_audio_path)
    if reference_path.is_file():
        reference_path.unlink(missing_ok=True)

    await repository.delete(voice)


@router.get("/voxcpm/voices/{voice_id}/reference/audio")
async def get_voxcpm_reference_audio(
    voice_id: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    repository = VoxCpmVoiceRepository(session)
    voice = await repository.get_by_id(voice_id)
    if not voice or not voice.reference_audio_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference audio not found.",
        )
    reference_path = Path(voice.reference_audio_path)
    if not reference_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference audio file is missing.",
        )
    return FileResponse(path=str(reference_path), media_type="audio/wav")


# ---- Phase 5: emotional generation ----


def _voxcpm_output_dir() -> Path:
    return settings.custom_voices_dir / "voxcpm2" / "generated"


@router.post("/voxcpm/generate", response_model=VoxCpmGenerateResponse)
async def generate_voxcpm_speech(
    request: VoxCpmGenerateRequest,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> VoxCpmGenerateResponse:
    """Emotional TTS from a cloned VoxCPM2 voice.

    reference audio = voice identity; emotion/instruction = performance.
    No fallback to other providers (plan rule).
    """
    from app.services.voxcpm_runtime import (
        VoxCpmRuntimeClient,
        VoxCpmRuntimeError,
        VoxCpmSynthesisRequest,
    )

    if not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Generation text must not be empty.",
        )
    if not (request.emotion or request.instruction):
        # Phase 5 is emotional TTS; a plain clone lives in Phase 4's
        # synthesize_clone. Requiring an emotion keeps the studio semantics.
        request = request.model_copy(update={"emotion": "neutral"})

    repository = VoxCpmVoiceRepository(session)
    voice = await repository.get_by_id(request.voice_id)
    if not voice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VoxCPM2 voice not found.",
        )
    reference_path = Path(voice.reference_audio_path)
    if not reference_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference audio file is missing.",
        )

    output_dir = _voxcpm_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{uuid.uuid4().hex}.wav"

    synthesis = VoxCpmSynthesisRequest(
        text=request.text,
        output_path=str(output_path),
        reference_wav_path=str(reference_path),
        instruction=request.instruction,
        cfg_value=request.cfg_value,
        inference_timesteps=request.inference_timesteps,
        seed=request.seed,
    )

    client = VoxCpmRuntimeClient(mock_mode=False)
    try:
        # Emotional generation needs the model: load it if the worker is cold.
        await client.load_model(voice.model_id or "openbmb/VoxCPM2", device="auto")
        try:
            result = await client.synthesize(synthesis, method="synthesize_emotional")
        except VoxCpmRuntimeError as exc:
            if exc.code == "VOXCPM_NOT_IMPLEMENTED":  # pragma: no cover - mock worker
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Emotional synthesis requires the real worker runtime.",
                ) from exc
            raise
    except VoxCpmRuntimeError as exc:
        code = exc.code
        if code == "VOXCPM_INVALID_PARAMS":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
        if code in ("VOXCPM_RUNTIME_NOT_INSTALLED", "VOXCPM_PACKAGE_NOT_INSTALLED"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="VoxCPM2 runtime is not installed. Install it from Settings.",
            ) from exc
        if code == "VOXCPM_REFERENCE_INVALID":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Reference audio is invalid for synthesis.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"VoxCPM2 synthesis failed: {exc.message}",
        ) from exc
    finally:
        await client.shutdown()

    duration, sample_rate, _channels = _read_wav_properties(output_path)
    return VoxCpmGenerateResponse(
        audio_url=f"/api/v1/voxcpm/generations/{output_path.stem}",
        output_path=str(output_path),
        sample_rate=sample_rate or result.sample_rate,
        duration_seconds=duration or result.duration_seconds,
        method=result.method or "synthesize_emotional",
        instruction=result.instruction if hasattr(result, "instruction") else None,
        voice_id=voice.id,
        emotion=request.emotion,
    )


@router.get("/voxcpm/generations/{generation_id}")
async def get_voxcpm_generation_audio(generation_id: str):
    """Serve a generated WAV by its stem id."""
    if not generation_id or "/" in generation_id or ".." in generation_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid generation id.")
    output_dir = _voxcpm_output_dir()
    generation_path = output_dir / f"{generation_id}.wav"
    if not generation_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation not found.")
    return FileResponse(path=str(generation_path), media_type="audio/wav")


# ---- Phase 10: Settings (installation) vs Runtime (process state) ----


def _lifecycle_http_error(exc: Exception) -> HTTPException:
    from app.services.voxcpm_lifecycle import VoxCpmLifecycleError

    if isinstance(exc, VoxCpmLifecycleError):
        if exc.code == "VOXCPM_RUNTIME_NOT_INSTALLED":
            return HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": exc.code, "message": exc.message},
            )
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message},
        )
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/voxcpm/installation")
async def get_voxcpm_installation():
    """Settings-tab snapshot: worker env + runtime package + model download."""
    from app.services.voxcpm_lifecycle import get_installation_status

    return get_installation_status()


@router.get("/voxcpm/installation/download-progress")
async def get_voxcpm_download_progress():
    """Coarse model download progress (bytes) for the Settings UI."""
    from app.services.voxcpm_lifecycle import model_download_progress

    return model_download_progress()


@router.post("/voxcpm/installation/install")
async def install_voxcpm_runtime():
    """Create the dedicated worker env and install the runtime (idempotent)."""
    from app.services.voxcpm_lifecycle import VoxCpmLifecycleError, install_runtime

    try:
        return install_runtime()
    except (VoxCpmLifecycleError, Exception) as exc:  # noqa: BLE001
        logger.exception("VoxCPM2 runtime install failed")
        raise _lifecycle_http_error(exc) from exc


@router.post("/voxcpm/installation/verify")
async def verify_voxcpm_installation():
    """Verify the dedicated env can import voxcpm (never the main env)."""
    from app.services.voxcpm_lifecycle import VoxCpmLifecycleError, verify_installation

    try:
        return verify_installation()
    except Exception as exc:  # noqa: BLE001
        raise _lifecycle_http_error(exc) from exc


@router.delete("/voxcpm/installation/env")
async def remove_voxcpm_env():
    """Remove the dedicated worker environment."""
    from app.services.voxcpm_lifecycle import remove_installation

    return remove_installation()


@router.delete("/voxcpm/installation/model")
async def remove_voxcpm_model():
    """Delete the downloaded HF model cache (~4.6 GB)."""
    from app.services.voxcpm_lifecycle import remove_model_cache

    return remove_model_cache()


@router.get("/voxcpm/runtime-state")
async def get_voxcpm_runtime_state():
    """Runtime-tab state: process/model/device — separate from installation."""
    from app.services.voxcpm_lifecycle import get_runtime_state

    return get_runtime_state()