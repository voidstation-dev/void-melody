"""Voice Design orchestration: previews → selected candidate → frozen voice."""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.omnivoice_voice import OmniVoiceVoiceModel
from app.providers.omnivoice_provider import OmniVoiceProvider
from app.services.omnivoice_model_service import (
    OMNI_ENGINE_VERSION,
    OMNI_MODEL_ID,
    OMNI_MODEL_REVISION,
    OMNI_PROMPT_FORMAT_VERSION,
    OmniVoiceModelService,
    omnivoice_model_service,
)
from app.services.omnivoice_runtime import OmniVoiceRuntimeClient
from app.services.voice_design.preview_store import (
    add_candidate,
    create_session,
    get_candidate_audio_path,
    load_session,
    mark_committed,
)
from app.services.voice_design.prompt_builder import compile_instruction

logger = logging.getLogger(__name__)

MAX_PREVIEW_CANDIDATES = 3
DEFAULT_PREVIEW_CANDIDATES = 3


class VoiceDesignError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PreviewResult:
    session_id: str
    compiled_instruction: str
    candidates: list[dict[str, Any]]


@dataclass(frozen=True)
class CommitResult:
    voice_id: str
    display_name: str
    provider_id: str
    engine_id: str
    voice_kind: str
    status: str


class VoiceDesignOrchestrator:
    """High-level Voice Design workflow.

    Stage 1 — Explore identity:
      instruct → preview candidates

    Stage 2 — Freeze identity:
      selected preview → VoiceClonePrompt → persistent OmniVoice voice
    """

    def __init__(
        self,
        *,
        model_service: OmniVoiceModelService | None = None,
        runtime_client: OmniVoiceRuntimeClient | None = None,
        provider: OmniVoiceProvider | None = None,
    ):
        self._model_service = model_service or omnivoice_model_service
        self._runtime = runtime_client or OmniVoiceRuntimeClient(
            default_timeout_seconds=settings.omnivoice_inference_timeout_seconds,
        )
        self._provider = provider or OmniVoiceProvider(runtime_client=self._runtime)

    def _ensure_ready(self) -> None:
        if not self._model_service.is_installed():
            raise VoiceDesignError(
                "OMNI_MODEL_NOT_INSTALLED",
                "G-OmniVoice model is not installed.",
            )

    async def _ensure_model_loaded(self) -> None:
        """Load the G-OmniVoice model into the worker if not already loaded."""
        try:
            model_path = self._model_service.resolve_model_path()
        except Exception as exc:
            raise VoiceDesignError(
                "OMNI_MODEL_NOT_INSTALLED",
                f"Could not resolve G-OmniVoice model path: {exc}",
            ) from exc

        try:
            info = await self._runtime.get_runtime_info()
            if info.get("model_loaded"):
                return
        except Exception:
            pass

        try:
            await self._runtime.load_model(str(model_path))
        except Exception as exc:
            raise VoiceDesignError(
                "OMNI_MODEL_LOAD_FAILED",
                f"Failed to load G-OmniVoice model: {exc}",
            ) from exc

    async def generate_previews(
        self,
        *,
        prompt: str | None = None,
        language: str | None = None,
        preview_text: str | None = None,
        count: int = DEFAULT_PREVIEW_CANDIDATES,
        attributes: dict[str, Any] | None = None,
    ) -> PreviewResult:
        """Generate up to *count* candidate preview voices for a design request."""
        self._ensure_ready()
        await self._ensure_model_loaded()
        attributes = attributes or {}
        compiled = compile_instruction(
            prompt=prompt,
            language=language,
            gender=attributes.get("gender"),
            age=attributes.get("age"),
            accent=attributes.get("accent"),
            pitch=attributes.get("pitch"),
            tone=attributes.get("tone"),
            style=attributes.get("style"),
            emotion=attributes.get("emotion"),
        )

        if not compiled.strip():
            raise VoiceDesignError(
                "VOICE_DESIGN_INVALID_PROMPT",
                "Voice design prompt is empty.",
            )

        if count < 1 or count > MAX_PREVIEW_CANDIDATES:
            raise VoiceDesignError(
                "VOICE_DESIGN_INVALID_PROMPT",
                f"Preview count must be between 1 and {MAX_PREVIEW_CANDIDATES}.",
            )

        preview_text = (preview_text or "").strip()
        if not preview_text:
            preview_text = "Xin chào, đây là giọng nói mẫu của tôi."

        session = create_session(
            compiled_instruction=compiled,
            preview_text=preview_text,
            language=language,
            metadata={"attributes": attributes},
        )

        candidate_ids = [str(uuid.uuid4())[:8] for _ in range(count)]
        candidates_info: list[dict[str, Any]] = []

        for idx, candidate_id in enumerate(candidate_ids):
            audio_path = Path(
                settings.audio_storage_dir
            ) / f"voice_design_{session.id}_{candidate_id}.wav"
            try:
                result = await self._provider.synthesize_preview(
                    text=preview_text,
                    instruction=compiled,
                    language=language,
                    rate=1.0,
                    destination_path=audio_path,
                )
            except Exception as exc:
                # Real backend may fail on the placeholder voice_type; mock succeeds.
                logger.warning("Preview candidate synthesis failed: %s", exc)
                raise VoiceDesignError(
                    "VOICE_DESIGN_PREVIEW_FAILED",
                    f"Failed to generate preview candidate {idx + 1}: {exc}",
                ) from exc

            add_candidate(
                session,
                candidate_id,
                Path(result.local_paths[0]) if result.local_paths else audio_path,
                seed=idx,
                attributes_json=None,
            )
            candidates_info.append(
                {
                    "id": candidate_id,
                    "audioUrl": f"/api/v1/tts/voice-design/sessions/{session.id}/candidates/{candidate_id}/audio",
                }
            )

        return PreviewResult(
            session_id=session.id,
            compiled_instruction=compiled,
            candidates=candidates_info,
        )

    async def commit_voice(
        self,
        session_id: str,
        candidate_id: str,
        display_name: str,
        session: AsyncSession,
        license_entitlement_id: str | None = None,
    ) -> CommitResult:
        """Freeze the selected candidate into a reusable OmniVoice voice."""
        self._ensure_ready()
        await self._ensure_model_loaded()
        preview_session = load_session(session_id)
        if preview_session is None:
            raise VoiceDesignError(
                "VOICE_DESIGN_SESSION_NOT_FOUND",
                f"Preview session '{session_id}' not found.",
            )

        if preview_session.status != "active":
            raise VoiceDesignError(
                "VOICE_DESIGN_SESSION_EXPIRED",
                f"Preview session '{session_id}' is no longer active.",
            )

        selected_audio = get_candidate_audio_path(session_id, candidate_id)
        if selected_audio is None:
            raise VoiceDesignError(
                "VOICE_DESIGN_CANDIDATE_NOT_FOUND",
                f"Candidate '{candidate_id}' not found in session '{session_id}'.",
            )

        voice_id = str(uuid.uuid4())
        voice_dir = Path(settings.custom_voices_dir) / "omnivoice" / voice_id
        voice_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = voice_dir / "voice-prompt.bin"
        preview_copy = voice_dir / "source-preview.wav"

        try:
            prompt_result = await self._runtime.create_voice_prompt(
                audio_path=str(selected_audio),
                transcript=preview_session.preview_text,
                output_path=str(prompt_path),
            )
        except Exception as exc:
            raise VoiceDesignError(
                "OMNI_PROMPT_CREATE_FAILED",
                f"Failed to create VoiceClonePrompt: {exc}",
            ) from exc

        # Persist selected preview as the canonical source audio for the voice.
        shutil.copy2(str(selected_audio), str(preview_copy))

        design_attributes_json = None
        metadata_attributes = preview_session.metadata.get("attributes")
        if metadata_attributes is not None:
            import json
            design_attributes_json = json.dumps(metadata_attributes)

        voice = OmniVoiceVoiceModel(
            id=voice_id,
            display_name=display_name,
            provider_id="omnivoice",
            engine_id="g-omnivoice",
            voice_kind="design",
            status="ready",
            design_prompt=preview_session.metadata.get("prompt"),
            compiled_instruction=preview_session.compiled_instruction,
            design_attributes_json=design_attributes_json,
            preview_text=preview_session.preview_text,
            selected_preview_audio_path=str(preview_copy),
            prompt_artifact_path=str(prompt_path),
            prompt_format_version=prompt_result.get(
                "format_version", OMNI_PROMPT_FORMAT_VERSION
            ),
            model_id=OMNI_MODEL_ID,
            model_revision=OMNI_MODEL_REVISION,
            engine_version=OMNI_ENGINE_VERSION,
            sample_rate=24000,
            voice_revision="v1",
            license_entitlement_id=license_entitlement_id,
        )
        session.add(voice)
        await session.commit()
        await session.refresh(voice)

        mark_committed(preview_session)

        return CommitResult(
            voice_id=voice.id,
            display_name=voice.display_name,
            provider_id=voice.provider_id,
            engine_id=voice.engine_id,
            voice_kind=voice.voice_kind,
            status=voice.status,
        )
