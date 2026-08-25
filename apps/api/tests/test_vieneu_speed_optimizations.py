"""Unit and regression tests for VieNeu Audio Studio speed optimizations."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.media.cache import (
    batch_store_cache_entries,
    batch_touch_cache_fingerprints,
    compute_segment_fingerprint,
    lookup_cache,
)
from app.media.pipeline import concat_audio_parts
from app.models.audio_cache import AudioSegmentCacheModel
from app.models.tts_job import TTSJobModel
from app.providers.base import ProviderResult
from app.providers.vieneu_provider import VieneuProvider
from app.services.chunk_executor import JobSnapshot
from app.services.prepared_voice import PreparedVoice
from app.services.vieneu_auto_tuner import run_autotune
from app.services.vieneu_resource_governor import VieNeuResourceGovernor
from app.services.vieneu_runtime_policy import (
    VieNeuRuntimeProfile,
    compute_hardware_key,
    generate_cpu_candidates,
    get_default_profile,
    persist_profile,
    load_persisted_profile,
)
from app.services.vieneu_text_planner import plan_vieneu_macro_chunks
from app.workers.tts_worker import execute_tts_job_step, process_chunk


def test_vieneu_macro_planner_splits_paragraphs_and_sentences():
    # 1. Short text returns single chunk
    short = "Xin chào các bạn."
    assert plan_vieneu_macro_chunks(short, target_chars=1024, hard_max_chars=1280) == [short]

    # 2. Text with paragraphs respects boundaries
    para1 = "Đây là đoạn văn thứ nhất dài vừa phải để kiểm tra việc phân chia macro block."
    para2 = "Đây là đoạn văn thứ hai có nội dung độc lập với đoạn thứ nhất."
    text = f"{para1}\n\n{para2}"
    chunks = plan_vieneu_macro_chunks(text, target_chars=50, hard_max_chars=100)
    assert len(chunks) == 2
    assert chunks[0] == para1
    assert chunks[1] == para2

    # 3. Long text splits cleanly without exceeding hard_max_chars
    long_text = " ".join(["Câu này có nhiều từ cần được chia nhỏ."] * 50)
    planned = plan_vieneu_macro_chunks(long_text, target_chars=500, hard_max_chars=600)
    assert len(planned) > 1
    for c in planned:
        assert len(c) <= 600
        assert c.strip()


def test_prepared_voice_properties():
    emb = np.zeros(192, dtype=np.float32)
    codes = np.zeros((1, 30), dtype=np.int32)

    v2_voice = PreparedVoice(
        voice_type="voice-v2",
        provider_id="vieneu",
        source="custom",
        voice_revision="rev-1",
        speaker_emb=emb,
        ref_codes=codes,
        clone_mode="fidelity",
        profile_format_version="vieneu-enrollment-v2",
    )
    assert v2_voice.is_enrollment_v2 is True
    spec = v2_voice.to_vieneu_voice_spec()
    assert isinstance(spec, dict)
    assert "speaker_emb" in spec
    assert "codes" in spec

    preset_voice = PreparedVoice(
        voice_type="Minh Đức",
        provider_id="vieneu",
        source="preset",
        voice_revision="preset:vieneu-v3turbo",
    )
    assert preset_voice.is_enrollment_v2 is False
    assert preset_voice.to_vieneu_voice_spec() == "Minh Đức"


@pytest.mark.asyncio
async def test_vieneu_zero_re_enrollment_during_synthesis():
    """Verify Audio Studio generation using valid Enrollment v2 profile calls prepare_reference ZERO times."""
    with patch("app.providers.vieneu_provider.ModelManager") as MockManager:
        mock_engine = MagicMock()
        mock_engine.infer = MagicMock(return_value=b"lossless_audio")
        mock_engine.save = MagicMock()
        mock_engine.prepare_reference = MagicMock()
        mock_engine.encode_reference = MagicMock()
        MockManager.return_value.get_engine = AsyncMock(return_value=mock_engine)

        provider = VieneuProvider()
        emb = np.zeros(192, dtype=np.float32)
        codes = np.zeros((1, 30), dtype=np.int32)
        prepared = PreparedVoice(
            voice_type="v2-clone",
            provider_id="vieneu",
            source="custom",
            voice_revision="v2",
            speaker_emb=emb,
            ref_codes=codes,
            clone_mode="fidelity",
            profile_format_version="vieneu-enrollment-v2",
            reference_audio_path="/tmp/original_ref.wav",
        )

        result = await provider.synthesize(
            text="Câu kiểm tra không re-enrollment.",
            voice_type="v2-clone",
            prepared_voice=prepared,
        )

        assert len(result.local_paths) == 1
        assert result.local_paths[0].endswith(".wav")
        # Critical assertion: prepare_reference and encode_reference were called ZERO times!
        mock_engine.prepare_reference.assert_not_called()
        mock_engine.encode_reference.assert_not_called()


@pytest.mark.asyncio
async def test_cache_fast_path_zero_copy(tmp_path, async_session_factory):
    # Store a dummy cache file
    cached_file = tmp_path / "cached_sample.wav"
    cached_file.write_bytes(b"RIFFdummywavdata")

    fp = compute_segment_fingerprint(
        provider_id="vieneu",
        text="cache test text",
        voice_type="Minh Đức",
    )

    async with async_session_factory() as session:
        entry = AudioSegmentCacheModel(
            fingerprint=fp,
            provider_id="vieneu",
            provider_version="v1",
            voice_key="Minh Đức",
            voice_revision="v1",
            text_hash="hash",
            audio_path=str(cached_file),
            mime_type="audio/wav",
            file_size=16,
        )
        session.add(entry)
        await session.commit()

    # Fast lookup with touch_db=False
    hit = await lookup_cache(fp, touch_db=False, session_factory=async_session_factory)
    assert hit is not None
    assert hit.audio_path == str(cached_file)

    # Batch touch
    await batch_touch_cache_fingerprints([fp], session_factory=async_session_factory)

    # Batch store new entries
    new_file = tmp_path / "new_part.wav"
    new_file.write_bytes(b"RIFFnewwavdata")
    new_fp = "new-fingerprint-123"

    await batch_store_cache_entries(
        [
            {
                "fingerprint": new_fp,
                "provider_id": "vieneu",
                "voice_key": "Minh Đức",
                "text": "new text",
                "source_audio_path": new_file,
                "mime_type": "audio/wav",
            }
        ],
        session_factory=async_session_factory,
    )

    async with async_session_factory() as session:
        stored = await session.get(AudioSegmentCacheModel, new_fp)
        assert stored is not None
        assert stored.voice_key == "Minh Đức"


def test_runtime_policy_candidates_and_profiles(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.vieneu_runtime_policy.get_profile_file_path", lambda: tmp_path / "profile.json")

    # Generate CPU candidates
    candidates = generate_cpu_candidates(cpu_count=8)
    assert len(candidates) >= 2
    for conc, threads in candidates:
        assert 1 <= conc <= 4
        assert threads >= 1

    # Hardware key computation
    hw_key = compute_hardware_key(device="cpu", backend="onnx", precision="int8")
    assert len(hw_key) == 32

    # Save and load profile
    prof = VieNeuRuntimeProfile(
        hardware_key=hw_key,
        device="cpu",
        backend="onnx",
        precision="int8",
        inference_concurrency=2,
        threads_per_inference=3,
        gpu_batch_size=1,
        performance_mode="auto",
        score=150.5,
    )
    persist_profile(prof)
    reloaded = load_persisted_profile()
    assert reloaded is not None
    assert reloaded.hardware_key == hw_key
    assert reloaded.inference_concurrency == 2
    assert reloaded.threads_per_inference == 3


def test_resource_governor_oom_fallback():
    gov = VieNeuResourceGovernor()
    gov._batch_size = 16
    assert gov.handle_cuda_oom() == 8
    assert gov.handle_cuda_oom() == 4
    assert gov.handle_cuda_oom() == 2
    assert gov.handle_cuda_oom() == 1
    assert gov.handle_cuda_oom() == 1  # Stays at 1
