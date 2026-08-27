import asyncio
import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import requests
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base
from app.exceptions import TTSJobError
from app.models.tts_job import TTSJobModel
from app.providers.base import ProviderResult
from app.workers.tts_worker import combine_audio_parts, execute_tts_job_step


@pytest.mark.asyncio
async def test_omnivoice_job_never_falls_back_to_capcut(
    async_session_factory,
    monkeypatch,
):
    async with async_session_factory() as session:
        job = TTSJobModel(
            text="hello",
            text_hash="omni-no-fallback",
            voice_type="omni-voice",
            voice_display_name="Omni voice",
            language_code="vi-VN",
            provider_id="omnivoice",
            status="queued",
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    capcut = MagicMock(side_effect=AssertionError("CapCut fallback used"))
    monkeypatch.setattr("app.workers.tts_worker.AsyncSessionLocal", async_session_factory)
    monkeypatch.setattr("app.workers.tts_worker.CapCutProvider", capcut)

    await execute_tts_job_step(job_id, provider_registry={})

    async with async_session_factory() as session:
        reloaded = await session.get(TTSJobModel, job_id)
        assert reloaded is not None
        assert reloaded.status == "failed"
        assert reloaded.error_code == "PROVIDER_NOT_CONFIGURED"
    capcut.assert_not_called()


class ConcatProcess:
    returncode = 0

    async def communicate(self):
        return b"", b""


@pytest.mark.asyncio
async def test_concat_writes_validated_output_atomically(tmp_path, monkeypatch):
    parts = [tmp_path / "part0.mp3", tmp_path / "part1.mp3"]
    for part in parts:
        part.write_bytes(b"ID3audio")
    destination = tmp_path / "job.mp3"

    async def fake_subprocess(*command, **kwargs):
        assert command[-2:] == ("mp3", str(Path(f"{destination}.tmp").absolute()))
        Path(command[-1]).write_bytes(b"ID3combined")
        return ConcatProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)

    await combine_audio_parts(parts=parts, destination=destination, rate=1.0)

    assert destination.read_bytes() == b"ID3combined"
    assert not Path(f"{destination}.tmp").exists()


class CommitGuardSession(AsyncSession):
    active_commits = 0

    async def commit(self):
        type(self).active_commits += 1
        try:
            if type(self).active_commits > 1:
                raise AssertionError("AsyncSession.commit called concurrently")
            await asyncio.sleep(0.01)
            return await super().commit()
        finally:
            type(self).active_commits -= 1


class ConcurrentFakeProvider:
    def __init__(self):
        self._lock = threading.Lock()
        self.active = 0
        self.max_active = 0

    async def synthesize(self, **kwargs):
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.03)
        with self._lock:
            self.active -= 1
        return ProviderResult(
            raw_response={"audio_url": "https://cdn.example/audio.mp3"},
            audio_urls=["https://cdn.example/audio.mp3"],
        )


@pytest.mark.asyncio
async def test_omnivoice_job_uses_omnivoice_chunk_concurrency(
    async_session_factory,
    tmp_path,
    monkeypatch,
):
    async with async_session_factory() as session:
        job = TTSJobModel(
            text="first. second.",
            text_hash="omni-chunk-concurrency",
            voice_type="omni-voice",
            voice_display_name="Omni voice",
            language_code="vi-VN",
            provider_id="omnivoice",
            status="queued",
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    observed_concurrency: list[int] = []

    async def capture_chunks(chunks, *, concurrency, process_chunk, is_cancelled):
        observed_concurrency.append(concurrency)
        if False:
            yield None

    monkeypatch.setattr("app.workers.tts_worker.AsyncSessionLocal", async_session_factory)
    monkeypatch.setattr("app.workers.tts_worker.execute_chunks_bounded", capture_chunks)
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path)

    await execute_tts_job_step(
        job_id,
        provider_registry={"omnivoice": ConcurrentFakeProvider()},
    )

    assert observed_concurrency == [1]


@pytest.mark.asyncio
async def test_worker_chunk_tasks_never_commit_shared_session(
    tmp_path,
    monkeypatch,
):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'worker.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(
        engine,
        class_=CommitGuardSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        job = TTSJobModel(
            text="first. second.",
            text_hash="hash-concurrent",
            voice_type="voice",
            voice_display_name="Voice",
            language_code="vi-VN",
            status="queued",
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    async def fake_download(*, url, destination, max_bytes):
        destination.write_bytes(b"ID3audio")
        return "audio/mpeg", 8

    async def fake_combine(*, parts, destination, rate, output_format="mp3", **kwargs):
        destination.write_bytes(b"ID3combined")

    provider = ConcurrentFakeProvider()
    monkeypatch.setattr("app.workers.tts_worker.AsyncSessionLocal", session_factory)
    monkeypatch.setattr(
        "app.workers.tts_worker.split_text_into_chunks",
        lambda text: ["first", "second"],
    )
    monkeypatch.setattr("app.workers.tts_worker.download_audio", fake_download)
    monkeypatch.setattr(
        "app.workers.tts_worker.combine_audio_parts",
        fake_combine,
        raising=False,
    )
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path)
    monkeypatch.setattr(settings, "tts_chunk_concurrency", 2, raising=False)
    monkeypatch.setattr(settings, "save_raw_provider_responses", False)

    try:
        await execute_tts_job_step(
            job_id, provider_registry={"capcut": provider}, worker_id=7
        )
        async with session_factory() as session:
            reloaded = await session.get(TTSJobModel, job_id)
            assert reloaded is not None
            assert reloaded.status == "completed"
            assert reloaded.progress == 100
            assert provider.max_active == 2
    finally:
        await engine.dispose()


class TimeoutProvider:
    def __init__(self):
        self.calls = 0

    async def synthesize(self, **kwargs):
        self.calls += 1
        raise requests.Timeout("provider timed out")


@pytest.mark.asyncio
async def test_worker_retries_timeout_twice_then_fails(
    async_session_factory,
    monkeypatch,
):
    async with async_session_factory() as session:
        job = TTSJobModel(
            text="hello",
            text_hash="retry-timeout",
            voice_type="voice",
            voice_display_name="Voice",
            language_code="vi-VN",
            status="queued",
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    provider = TimeoutProvider()
    delayed_enqueue = AsyncMock()
    worker_sleep = AsyncMock()
    monkeypatch.setattr(
        "app.workers.tts_worker.AsyncSessionLocal", async_session_factory
    )
    monkeypatch.setattr(
        "app.workers.queue_manager.queue_manager.enqueue_after",
        delayed_enqueue,
        raising=False,
    )
    monkeypatch.setattr("app.workers.tts_worker.asyncio.sleep", worker_sleep)
    monkeypatch.setattr(settings, "tts_max_auto_retries", 2, raising=False)
    monkeypatch.setattr(settings, "tts_retry_base_delay_seconds", 2, raising=False)

    await execute_tts_job_step(job_id, provider_registry={"capcut": provider})
    await execute_tts_job_step(job_id, provider_registry={"capcut": provider})
    await execute_tts_job_step(job_id, provider_registry={"capcut": provider})

    async with async_session_factory() as session:
        reloaded = await session.get(TTSJobModel, job_id)
        assert reloaded is not None
        assert reloaded.status == "failed"
        assert reloaded.error_code == "PROVIDER_TIMEOUT"
        assert reloaded.attempt_count == 3
    assert provider.calls == 3
    assert delayed_enqueue.await_count == 2
    worker_sleep.assert_not_awaited()


class SuccessfulProvider:
    def __init__(self):
        self.rates: list[float] = []

    async def synthesize(self, **kwargs):
        self.rates.append(kwargs["rate"])
        return ProviderResult(
            raw_response={"audio_url": "https://cdn.example/audio.mp3"},
            audio_urls=["https://cdn.example/audio.mp3"],
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("ffmpeg_fallback", "expected_provider_rate", "expected_ffmpeg_rate"),
    [(False, 1.5, 1.0), (True, 1.0, 1.5)],
)
async def test_worker_applies_rate_in_exactly_one_stage(
    async_session_factory,
    tmp_path,
    monkeypatch,
    ffmpeg_fallback,
    expected_provider_rate,
    expected_ffmpeg_rate,
):
    async with async_session_factory() as session:
        job = TTSJobModel(
            text="hello",
            text_hash=f"rate-{ffmpeg_fallback}",
            voice_type="voice",
            voice_display_name="Voice",
            language_code="vi-VN",
            rate=1.5,
            status="queued",
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    async def fake_download(*, url, destination, max_bytes):
        destination.write_bytes(b"ID3audio")
        return "audio/mpeg", 8

    ffmpeg_rates: list[float] = []

    async def fake_combine(*, parts, destination, rate, output_format="mp3", **kwargs):
        ffmpeg_rates.append(rate)
        destination.write_bytes(b"ID3combined")

    provider = SuccessfulProvider()
    monkeypatch.setattr(
        "app.workers.tts_worker.AsyncSessionLocal", async_session_factory
    )
    monkeypatch.setattr("app.workers.tts_worker.download_audio", fake_download)
    monkeypatch.setattr("app.workers.tts_worker.combine_audio_parts", fake_combine)
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path)
    monkeypatch.setattr(
        settings,
        "tts_apply_rate_with_ffmpeg",
        ffmpeg_fallback,
        raising=False,
    )

    await execute_tts_job_step(job_id, provider_registry={"capcut": provider})

    assert provider.rates == [expected_provider_rate]
    assert ffmpeg_rates == [expected_ffmpeg_rate]


@pytest.mark.asyncio
async def test_ffmpeg_failure_does_not_retry_provider(
    async_session_factory,
    tmp_path,
    monkeypatch,
):
    async with async_session_factory() as session:
        job = TTSJobModel(
            text="hello",
            text_hash="ffmpeg-failure",
            voice_type="voice",
            voice_display_name="Voice",
            language_code="vi-VN",
            status="queued",
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    async def fake_download(*, url, destination, max_bytes):
        destination.write_bytes(b"ID3audio")
        return "audio/mpeg", 8

    async def fail_combine(*, parts, destination, rate, output_format="mp3", **kwargs):
        raise TTSJobError(
            code="FFMPEG_FAILED",
            message="concat failed",
            retryable=False,
        )

    provider = SuccessfulProvider()
    delayed_enqueue = AsyncMock()
    monkeypatch.setattr(
        "app.workers.tts_worker.AsyncSessionLocal", async_session_factory
    )
    monkeypatch.setattr("app.workers.tts_worker.download_audio", fake_download)
    monkeypatch.setattr("app.workers.tts_worker.combine_audio_parts", fail_combine)
    monkeypatch.setattr(
        "app.workers.queue_manager.queue_manager.enqueue_after",
        delayed_enqueue,
        raising=False,
    )
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path)

    await execute_tts_job_step(job_id, provider_registry={"capcut": provider})

    async with async_session_factory() as session:
        reloaded = await session.get(TTSJobModel, job_id)
        assert reloaded is not None
        assert reloaded.status == "failed"
        assert reloaded.error_code == "FFMPEG_FAILED"
    assert provider.rates == [1.0]
    delayed_enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_final_output_is_failed_and_removed(
    async_session_factory,
    tmp_path,
    monkeypatch,
):
    async with async_session_factory() as session:
        job = TTSJobModel(
            text="hello",
            text_hash="invalid-final",
            voice_type="voice",
            voice_display_name="Voice",
            language_code="vi-VN",
            status="queued",
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    async def fake_download(*, url, destination, max_bytes):
        destination.write_bytes(b"ID3audio")
        return "audio/mpeg", 8

    async def invalid_combine(*, parts, destination, rate, output_format="mp3", **kwargs):
        destination.write_bytes(b"not audio")

    monkeypatch.setattr(
        "app.workers.tts_worker.AsyncSessionLocal", async_session_factory
    )
    monkeypatch.setattr("app.workers.tts_worker.download_audio", fake_download)
    monkeypatch.setattr("app.workers.tts_worker.combine_audio_parts", invalid_combine)
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path)

    await execute_tts_job_step(
        job_id, provider_registry={"capcut": SuccessfulProvider()}
    )

    async with async_session_factory() as session:
        reloaded = await session.get(TTSJobModel, job_id)
        assert reloaded is not None
        assert reloaded.status == "failed"
        assert reloaded.error_code == "AUDIO_INVALID_CONTENT"
    assert not (tmp_path / f"{job_id}.mp3").exists()
    assert list(tmp_path.glob(f"{job_id}_part*.mp3")) == []


@pytest.mark.asyncio
async def test_successful_job_does_not_persist_raw_provider_response(
    async_session_factory,
    tmp_path,
    monkeypatch,
):
    async with async_session_factory() as session:
        job = TTSJobModel(
            text="hello",
            text_hash="raw-success",
            voice_type="voice",
            voice_display_name="Voice",
            language_code="vi-VN",
            status="queued",
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    async def fake_download(*, url, destination, max_bytes):
        destination.write_bytes(b"ID3audio")
        return "audio/mpeg", 8

    async def fake_combine(*, parts, destination, rate, output_format="mp3", **kwargs):
        destination.write_bytes(b"ID3combined")

    raw_directory = tmp_path / "raw"
    monkeypatch.setattr(
        "app.workers.tts_worker.AsyncSessionLocal", async_session_factory
    )
    monkeypatch.setattr("app.workers.tts_worker.download_audio", fake_download)
    monkeypatch.setattr("app.workers.tts_worker.combine_audio_parts", fake_combine)
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path)
    monkeypatch.setattr(settings, "raw_response_dir", raw_directory)
    monkeypatch.setattr(settings, "save_raw_provider_responses", True)

    await execute_tts_job_step(
        job_id, provider_registry={"capcut": SuccessfulProvider()}
    )

    assert list(raw_directory.glob("*.json")) == []
