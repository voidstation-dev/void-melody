"""Phase 3 tests: VoxCPM2 voice storage, clone-profile CRUD, and API endpoints.

Covers:
- tts_voxcpm_voices model defaults + repository CRUD
- /api/v1/voxcpm/voices endpoints (analyze, create, list, get, delete, reference audio)
- provider isolation: provider_id stays "voxcpm2", no tts_custom_voices reuse
- path validation / consent / format gates
"""

import io
import math
import struct
import wave
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_async_session
from app.main import app
from app.db.repositories.voxcpm_voices import VoxCpmVoiceRepository
from app.models.voxcpm_voice import VoxCpmVoiceModel
from tests.conftest import pro_entitlement_auth

# ---------------------------------------------------------------------------
# Fake reference audio helpers
# ---------------------------------------------------------------------------


def make_tone_wav(duration_seconds: float = 6.0, sample_rate: int = 16000) -> bytes:
    """Generate a valid PCM16 mono WAV with a modulated tone (speech-like)."""
    frames = bytearray()
    total = int(duration_seconds * sample_rate)
    for i in range(total):
        t = i / sample_rate
        # amplitude envelope to create speech/silence pattern
        envelope = 0.5 + 0.5 * math.sin(2 * math.pi * 0.7 * t)
        value = int(20000 * envelope * math.sin(2 * math.pi * 220 * t))
        frames += struct.pack("<h", value)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(bytes(frames))
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def _pro_auth(pro_entitlement_auth):  # noqa: F811
    yield


test_engine = create_async_engine(
    "sqlite+aiosqlite:///file:memdb_voxcpm?mode=memory&cache=shared&uri=true", echo=False
)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_async_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    app.dependency_overrides[get_async_session] = override_get_async_session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_async_session, None)


@pytest.fixture
def patch_storage(tmp_path: Path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "custom_voices_dir", tmp_path / "voices")
    monkeypatch.setattr(settings, "tts_audio_max_bytes", 50 * 1024 * 1024)
    (tmp_path / "voices").mkdir(parents=True, exist_ok=True)
    return tmp_path / "voices"


# ---------------------------------------------------------------------------
# Model + repository unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_model_defaults_are_voxcpm2():
    session = TestSessionLocal()
    voice = VoxCpmVoiceModel(display_name="Defaults", reference_audio_path="x.wav")
    session.add(voice)
    await session.flush()
    assert voice.provider_id == "voxcpm2"
    assert voice.engine_id == "voxcpm2"
    assert voice.status == "ready"
    assert voice.model_id == "openbmb/VoxCPM2"
    await session.rollback()
    await session.close()


@pytest.mark.asyncio
async def test_repository_save_and_get():
    session = TestSessionLocal()
    repository = VoxCpmVoiceRepository(session)
    voice = VoxCpmVoiceModel(
        display_name="Repo Voice",
        reference_audio_path="/tmp/ref.wav",
        reference_duration_seconds=5.0,
        quality_score=85,
    )
    saved = await repository.save(voice)
    assert saved.id
    fetched = await repository.get_by_id(saved.id)
    assert fetched is not None
    assert fetched.display_name == "Repo Voice"
    assert fetched.provider_id == "voxcpm2"
    await session.close()


@pytest.mark.asyncio
async def test_repository_list_and_delete():
    session = TestSessionLocal()
    repository = VoxCpmVoiceRepository(session)
    await repository.save(VoxCpmVoiceModel(display_name="Alpha", reference_audio_path="a.wav"))
    await repository.save(VoxCpmVoiceModel(display_name="Beta", reference_audio_path="b.wav"))
    voices = await repository.list_voices()
    names = [v.display_name for v in voices]
    assert "Alpha" in names and "Beta" in names
    target = next(v for v in voices if v.display_name == "Beta")
    await repository.delete(target)
    remaining = await repository.list_voices()
    assert all(v.display_name != "Beta" for v in remaining)
    await session.close()


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_reference_rejects_unsupported_format():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/voxcpm/voices/analyze",
            files={"audio_file": ("test.txt", io.BytesIO(b"nope"), "text/plain")},
            headers={"X-Melody-Token": "test-token", "X-License-Key": "dev"},
        )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "UNSUPPORTED_FORMAT"


@pytest.mark.asyncio
async def test_analyze_reference_returns_analysis(patch_storage):
    wav_bytes = make_tone_wav(6.0)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/voxcpm/voices/analyze",
            files={"audio_file": ("tone.wav", io.BytesIO(wav_bytes), "audio/wav")},
            headers={"X-Melody-Token": "test-token", "X-License-Key": "dev"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["quality_score"] >= 0
    assert payload["source_duration_seconds"] >= 3.0
    assert len(payload["waveform_peaks"]) > 0
    assert "warnings" in payload


@pytest.mark.asyncio
async def test_create_voice_requires_consent():
    wav_bytes = make_tone_wav(6.0)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/voxcpm/voices",
            data={"display_name": "No Consent", "consent_given": "false"},
            files={"audio_file": ("tone.wav", io.BytesIO(wav_bytes), "audio/wav")},
            headers={"X-Melody-Token": "test-token", "X-License-Key": "dev"},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_voice_full_flow(patch_storage, tmp_path):
    """Upload → analyze → trim → save → DB row + canonical reference WAV."""
    wav_bytes = make_tone_wav(6.0)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/voxcpm/voices",
            data={
                "display_name": "Giọng thử nghiệm",
                "consent_given": "true",
                "description": "demo",
                "reference_transcript": "Xin chào thế giới",
            },
            files={"audio_file": ("tone.wav", io.BytesIO(wav_bytes), "audio/wav")},
            headers={"X-Melody-Token": "test-token", "X-License-Key": "dev"},
        )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["provider_id"] == "voxcpm2"
    assert payload["engine_id"] == "voxcpm2"
    assert payload["status"] == "ready"
    assert payload["display_name"] == "Giọng thử nghiệm"
    assert payload["reference_transcript"] == "Xin chào thế giới"
    assert payload["quality_score"] is not None

    # Canonical reference WAV exists on disk and is a bounded mono 16k WAV
    from app.config import settings

    stored = list((patch_storage / "voxcpm2").glob("*.wav"))
    assert len(stored) == 1
    with wave.open(str(stored[0]), "rb") as ref:
        assert ref.getnchannels() == 1
        assert ref.getsampwidth() == 2
        assert 3.0 <= ref.getnframes() / ref.getframerate() <= 8.0 + 0.05
        sample_rate = ref.getframerate()

    assert payload["reference_sample_rate"] == sample_rate

    # DB row references exactly that file
    session = TestSessionLocal()
    repository = VoxCpmVoiceRepository(session)
    db_voice = await repository.get_by_id(payload["id"])
    assert db_voice is not None
    assert Path(db_voice.reference_audio_path) == stored[0]
    await session.close()


@pytest.mark.asyncio
async def test_create_voice_duplicate_name_conflict(patch_storage):
    wav_bytes = make_tone_wav(6.0)
    headers = {"X-Melody-Token": "test-token", "X-License-Key": "dev"}
    data = {"display_name": "Trùng tên", "consent_given": "true"}
    files = {"audio_file": ("tone.wav", io.BytesIO(wav_bytes), "audio/wav")}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post("/api/v1/voxcpm/voices", data=data, files=files, headers=headers)
        assert first.status_code == 201
        second = await client.post("/api/v1/voxcpm/voices", data=data, files=files, headers=headers)
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "DUPLICATE_NAME"


@pytest.mark.asyncio
async def test_create_voice_rejects_too_short_audio(patch_storage):
    wav_bytes = make_tone_wav(1.5)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/voxcpm/voices",
            data={"display_name": "Ngắn", "consent_given": "true"},
            files={"audio_file": ("short.wav", io.BytesIO(wav_bytes), "audio/wav")},
            headers={"X-Melody-Token": "test-token", "X-License-Key": "dev"},
        )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "TOO_SHORT"


@pytest.mark.asyncio
async def test_list_get_delete_flow(patch_storage):
    wav_bytes = make_tone_wav(6.0)
    headers = {"X-Melody-Token": "test-token", "X-License-Key": "dev"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/v1/voxcpm/voices",
            data={"display_name": "CRUD Voice", "consent_given": "true"},
            files={"audio_file": ("tone.wav", io.BytesIO(wav_bytes), "audio/wav")},
            headers=headers,
        )
        assert created.status_code == 201
        voice_id = created.json()["id"]

        listed = await client.get("/api/v1/voxcpm/voices", headers=headers)
        assert listed.status_code == 200
        body = listed.json()
        assert body["total"] >= 1
        assert any(v["id"] == voice_id for v in body["items"])

        got = await client.get(f"/api/v1/voxcpm/voices/{voice_id}", headers=headers)
        assert got.status_code == 200
        assert got.json()["display_name"] == "CRUD Voice"

        audio = await client.get(f"/api/v1/voxcpm/voices/{voice_id}/reference/audio", headers=headers)
        assert audio.status_code == 200
        assert audio.headers["content-type"].startswith("audio/wav")
        assert len(audio.content) > 0

        deleted = await client.delete(f"/api/v1/voxcpm/voices/{voice_id}", headers=headers)
        assert deleted.status_code == 204

        gone = await client.get(f"/api/v1/voxcpm/voices/{voice_id}", headers=headers)
        assert gone.status_code == 404


@pytest.mark.asyncio
async def test_get_unknown_voice_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/voxcpm/voices/nonexistent-id",
            headers={"X-Melody-Token": "test-token", "X-License-Key": "dev"},
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_voice_does_not_touch_tts_custom_voices(patch_storage):
    """Provider isolation: creating a VoxCPM2 voice must not write to the
    VieNeu custom-voices table or reuse tts_custom_voices storage."""
    wav_bytes = make_tone_wav(6.0)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/voxcpm/voices",
            data={"display_name": "Isolation Check", "consent_given": "true"},
            files={"audio_file": ("tone.wav", io.BytesIO(wav_bytes), "audio/wav")},
            headers={"X-Melody-Token": "test-token", "X-License-Key": "dev"},
        )
    assert response.status_code == 201

    from app.models.custom_voice import CustomVoiceModel

    session = TestSessionLocal()
    count = (await session.execute(__import__("sqlalchemy").select(CustomVoiceModel))).scalars().all()
    assert count == []
    await session.close()

# ---------------------------------------------------------------------------
# Phase 5: emotional generation endpoints
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_runtime(monkeypatch):
    """Replace VoxCpmRuntimeClient with a controllable fake.

    Records constructor mock_mode (must be False — real worker, no fallback),
    simulates a successful emotional synthesis writing a real 48 kHz WAV.
    """
    import wave as wave_mod

    calls: dict = {}

    class FakeSynthesisResult:
        def __init__(self, output_path: str, sample_rate: int, duration_seconds: float, method: str):
            self.output_path = output_path
            self.sample_rate = sample_rate
            self.duration_seconds = duration_seconds
            self.method = method
            self.instruction = "Sad, restrained"

    class FakeClient:
        def __init__(self, *args, **kwargs):
            calls["mock_mode"] = kwargs.get("mock_mode")
            calls["load_model_args"] = None
            calls["synth"] = None
            calls["shutdown"] = 0

        async def load_model(self, model_id="openbmb/VoxCPM2", device="auto"):
            calls["load_model_args"] = (model_id, device)
            return {"status": "loaded"}

        async def synthesize(self, request, *, method="synthesize_clone", timeout_seconds=None):
            calls["synth"] = {
                "method": method,
                "timeout": timeout_seconds,
                "text": request.text,
                "reference": request.reference_wav_path,
                "instruction": request.instruction,
                "emotion": request.emotion,
                "output_path": request.output_path,
            }
            out = Path(request.output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            frames = int(48000 * 1.5)
            with wave_mod.open(str(out), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(48000)
                w.writeframes(b"\x00\x00" * frames)
            return FakeSynthesisResult(str(out), 48000, 1.5, method)

        async def shutdown(self):
            calls["shutdown"] += 1

    from app.services import voxcpm_runtime as rt_module

    monkeypatch.setattr(rt_module, "VoxCpmRuntimeClient", FakeClient)
    # The endpoint imports the names lazily inside the function body from
    # app.services.voxcpm_runtime, so patching the module attribute works.
    return calls


@pytest.mark.asyncio
async def test_generate_emotional_flow(patch_storage, fake_runtime, pro_entitlement_auth):  # noqa: F811
    # create a voice first (direct DB insert keeps this test focused)
    session = TestSessionLocal()
    ref_dir = patch_storage / "voxcpm2"
    ref_dir.mkdir(parents=True, exist_ok=True)
    ref_path = ref_dir / "ref.wav"
    ref_path.write_bytes(make_tone_wav(2.0))
    voice = VoxCpmVoiceModel(
        id="gen-voice-1",
        display_name="Gen Voice",
        reference_audio_path=str(ref_path),
    )
    session.add(voice)
    await session.commit()
    await session.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/voxcpm/generate",
            json={
                "voice_id": "gen-voice-1",
                "text": "Anh vẫn nhớ ngày hôm đó.",
                "emotion": "sad",
            },
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sample_rate"] == 48000
    assert body["method"] == "synthesize_emotional"
    assert body["voice_id"] == "gen-voice-1"
    assert body["emotion"] == "sad"
    assert body["audio_url"].startswith("/api/v1/voxcpm/generations/")
    assert fake_runtime["mock_mode"] is False  # real worker, never mock
    assert fake_runtime["synth"]["method"] == "synthesize_emotional"
    assert fake_runtime["shutdown"] >= 1


@pytest.mark.asyncio
async def test_generate_unknown_voice_404(patch_storage, fake_runtime):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/voxcpm/generate",
            json={"voice_id": "nope", "text": "hi", "emotion": "sad"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_generate_empty_text_400(patch_storage, fake_runtime):
    session = TestSessionLocal()
    ref_dir = patch_storage / "voxcpm2"
    ref_dir.mkdir(parents=True, exist_ok=True)
    ref_path = ref_dir / "ref2.wav"
    ref_path.write_bytes(make_tone_wav(2.0))
    voice = VoxCpmVoiceModel(
        id="gen-voice-2",
        display_name="Gen Voice 2",
        reference_audio_path=str(ref_path),
    )
    session.add(voice)
    await session.commit()
    await session.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/voxcpm/generate",
            json={"voice_id": "gen-voice-2", "text": "   ", "emotion": "sad"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_generation_audio_serving(patch_storage, fake_runtime, pro_entitlement_auth):  # noqa: F811
    session = TestSessionLocal()
    ref_dir = patch_storage / "voxcpm2"
    ref_dir.mkdir(parents=True, exist_ok=True)
    ref_path = ref_dir / "ref3.wav"
    ref_path.write_bytes(make_tone_wav(2.0))
    voice = VoxCpmVoiceModel(
        id="gen-voice-3",
        display_name="Gen Voice 3",
        reference_audio_path=str(ref_path),
    )
    session.add(voice)
    await session.commit()
    await session.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        gen = await client.post(
            "/api/v1/voxcpm/generate",
            json={"voice_id": "gen-voice-3", "text": "Xin chào", "instruction": "slow, warm"},
        )
        assert gen.status_code == 200
        stem = gen.json()["audio_url"].rsplit("/", 1)[-1]
        audio = await client.get(f"/api/v1/voxcpm/generations/{stem}")
        assert audio.status_code == 200
        assert audio.headers["content-type"].startswith("audio/wav")
        # custom instruction passes through to the worker
        assert fake_runtime["synth"]["instruction"] == "slow, warm"

        missing = await client.get("/api/v1/voxcpm/generations/doesnotexist")
        assert missing.status_code == 404

        traversal = await client.get("/api/v1/voxcpm/generations/..%2F..%2Fetc")
        assert traversal.status_code in (400, 404)  # must never serve files

        # Windows path traversal: backslashes are separators on nt, so a
        # drive-letter/UNC generation id must be rejected outright, not
        # resolved to an absolute path outside the output dir.
        backslash = await client.get(
            "/api/v1/voxcpm/generations/C%3A%5CUsers%5Cvictim%5Cprivate%5Crecording"
        )
        assert backslash.status_code in (400, 404)
        unc = await client.get(
            "/api/v1/voxcpm/generations/%5C%5Cserver%5Cshare%5Cf"
        )
        assert unc.status_code in (400, 404)


@pytest.mark.asyncio
async def test_generate_emotion_reaches_worker(patch_storage, fake_runtime, pro_entitlement_auth):  # noqa: F811
    """The selected emotion preset must ride into VoxCpmSynthesisRequest —
    the worker's _resolve_instruction is what compiles presets to
    performance text, so dropping the field silently degrades to neutral."""
    session = TestSessionLocal()
    ref_dir = patch_storage / "voxcpm2"
    ref_dir.mkdir(parents=True, exist_ok=True)
    ref_path = ref_dir / "ref-e.wav"
    ref_path.write_bytes(make_tone_wav(2.0))
    session.add(VoxCpmVoiceModel(
        id="gen-voice-e",
        display_name="Gen Voice E",
        reference_audio_path=str(ref_path),
    ))
    await session.commit()
    await session.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/voxcpm/generate",
            json={"voice_id": "gen-voice-e", "text": "Hôm nay trời đẹp.", "emotion": "cheerful"},
        )
    assert resp.status_code == 200, resp.text
    assert fake_runtime["synth"]["emotion"] == "cheerful"
    # Direct endpoint must honor the queue-lane inference budget — a 60s
    # RPC default kills CPU synthesis long before the worker finishes.
    from app.config import settings
    assert fake_runtime["synth"]["timeout"] == settings.voxcpm_inference_timeout_seconds


@pytest.mark.asyncio
async def test_generate_without_worker_env_is_409_not_500(patch_storage, monkeypatch):
    """When the dedicated worker env is absent, the VoxCpmRuntimeClient
    constructor raises VoxCpmEnvError. The handler must translate that into
    the same 409 as its other not-installed branches, not an unhandled 500."""
    import wave as wave_mod

    from app.services.voxcpm_env import VoxCpmEnvError

    def raise_env_error(*args, **kwargs):
        raise VoxCpmEnvError(
            "VOXCPM_RUNTIME_NOT_INSTALLED",
            "VoxCPM2 worker env not found. Install the runtime from Settings first.",
        )

    monkeypatch.setattr(
        "app.services.voxcpm_runtime.VoxCpmRuntimeClient", raise_env_error
    )

    session = TestSessionLocal()
    ref_dir = patch_storage / "voxcpm2"
    ref_dir.mkdir(parents=True, exist_ok=True)
    ref_path = ref_dir / "ref-n.wav"
    frames = int(16000 * 1.0)
    with wave_mod.open(str(ref_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * frames)
    session.add(VoxCpmVoiceModel(
        id="gen-voice-n",
        display_name="Gen Voice N",
        reference_audio_path=str(ref_path),
    ))
    await session.commit()
    await session.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/voxcpm/generate",
            json={"voice_id": "gen-voice-n", "text": "Kiểm tra", "emotion": "sad"},
        )
    assert resp.status_code == 409, resp.text


# ---------------------------------------------------------------------------
# Phase 7 — Shared Voice Library integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shared_custom_voices_list_includes_voxcpm2():
    """VoxCPM2 voices appear in the shared /tts/voices/custom library."""
    session = TestSessionLocal()
    session.add(VoxCpmVoiceModel(
        id="vox-lib-1",
        display_name="Library Vox Voice",
        reference_audio_path="/tmp/ref.wav",
        reference_duration_seconds=4.2,
        quality_score=88,
    ))
    await session.commit()
    await session.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/tts/voices/custom")
        assert resp.status_code == 200
        items = resp.json()["items"]
        vox = [v for v in items if v["id"] == "vox-lib-1"]
        assert len(vox) == 1
        assert vox[0]["provider_id"] == "voxcpm2"
        assert vox[0]["status"] == "ready"
        assert vox[0]["reference_duration_seconds"] == 4.2
        assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_shared_custom_voice_get_by_id_resolves_voxcpm2():
    session = TestSessionLocal()
    session.add(VoxCpmVoiceModel(
        id="vox-lib-2",
        display_name="Get Me",
        reference_audio_path="/tmp/ref.wav",
    ))
    await session.commit()
    await session.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/tts/voices/custom/vox-lib-2")
        assert resp.status_code == 200
        assert resp.json()["provider_id"] == "voxcpm2"


@pytest.mark.asyncio
async def test_shared_custom_voice_delete_removes_voxcpm2(patch_storage):
    ref_dir = patch_storage / "voxcpm2" / "vox-lib-3"
    ref_dir.mkdir(parents=True, exist_ok=True)
    (ref_dir / "reference.wav").write_bytes(make_tone_wav(1.0))

    session = TestSessionLocal()
    session.add(VoxCpmVoiceModel(
        id="vox-lib-3",
        display_name="Delete Me",
        reference_audio_path=str(ref_dir / "reference.wav"),
    ))
    await session.commit()
    await session.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete("/api/v1/tts/voices/custom/vox-lib-3")
        assert resp.status_code == 204

    session = TestSessionLocal()
    gone = await session.get(VoxCpmVoiceModel, "vox-lib-3")
    await session.close()
    assert gone is None
    assert not ref_dir.exists() or not any(ref_dir.iterdir())


@pytest.mark.asyncio
async def test_no_id_collision_between_voxcpm2_and_vieneu_custom_voices():
    """Provider-aware identity: the same id can exist in both providers
    without the shared list collapsing them."""
    session = TestSessionLocal()
    session.add(VoxCpmVoiceModel(
        id="shared-id-1",
        display_name="VoxCPM2 version",
        reference_audio_path="/tmp/ref.wav",
    ))
    from app.models.custom_voice import CustomVoiceModel

    session.add(CustomVoiceModel(
        id="shared-id-1",
        display_name="VieNeu version",
        transcript="",
        consent_given=True,
        consent_version="v1",
        provider_id="vieneu",
        engine_id="vieneu",
        status="ready",
        reference_audio_path="/tmp/ref.wav",
    ))
    await session.commit()
    await session.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/tts/voices/custom")
        assert resp.status_code == 200
        items = [v for v in resp.json()["items"] if v["id"] == "shared-id-1"]
        assert len(items) == 2
        assert {v["provider_id"] for v in items} == {"voxcpm2", "vieneu"}
