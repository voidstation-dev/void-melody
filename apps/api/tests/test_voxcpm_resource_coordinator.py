"""Phase 9 tests: SpeechRuntimeCoordinator + VoxCPM2 resource management.

Plan policy: only one heavy GPU speech runtime active when VRAM is
constrained. VoxCPM2 is NOT inside vieneu_resource_governor. Unload-before-
load with explicit user messaging, no silent fallback.
"""

import pytest

from app.providers.voxcpm_provider import VoxCpmProvider, VoxCpmProviderError
from app.services.speech_runtime_coordinator import (
    SpeechRuntimeCoordinator,
    SpeechRuntimeCoordinatorError,
    speech_runtime_coordinator,
)


@pytest.mark.asyncio
async def test_coordinator_unloads_other_loaded_runtime_before_load():
    coordinator = SpeechRuntimeCoordinator()
    unloaded: list[str] = []

    async def unload_a():
        unloaded.append("a")

    coordinator.register("a", unload=unload_a, is_loaded=lambda: True)
    coordinator.register("b", unload=lambda: None, is_loaded=lambda: False)

    result = await coordinator.acquire_exclusive("voxcpm2")
    assert unloaded == ["a"]
    assert result == ["a"]


@pytest.mark.asyncio
async def test_coordinator_does_not_unload_requester_itself():
    coordinator = SpeechRuntimeCoordinator()
    unloaded: list[str] = []

    async def unload_self():
        unloaded.append("voxcpm2")

    coordinator.register("voxcpm2", unload=unload_self, is_loaded=lambda: True)
    result = await coordinator.acquire_exclusive("voxcpm2")
    assert unloaded == []
    assert result == []


@pytest.mark.asyncio
async def test_coordinator_raises_explicitly_when_unload_fails():
    coordinator = SpeechRuntimeCoordinator()

    async def failing_unload():
        raise RuntimeError("worker crashed")

    coordinator.register("omnivoice", unload=failing_unload, is_loaded=lambda: True)

    with pytest.raises(SpeechRuntimeCoordinatorError) as exc_info:
        await coordinator.acquire_exclusive("voxcpm2")
    assert exc_info.value.code == "SPEECH_RUNTIME_UNLOAD_FAILED"
    assert "omnivoice" in exc_info.value.message


@pytest.mark.asyncio
async def test_coordinator_probe_failure_is_not_fatal():
    coordinator = SpeechRuntimeCoordinator()
    calls = []

    async def unload():
        calls.append(1)

    def broken_probe():
        raise RuntimeError("probe broken")

    coordinator.register("broken", unload=unload, is_loaded=broken_probe)
    # Must not raise; broken probe treated as not loaded.
    result = await coordinator.acquire_exclusive("voxcpm2")
    assert result == []
    assert calls == []


def test_loaded_runtimes_reports_state():
    coordinator = SpeechRuntimeCoordinator()
    coordinator.register("a", unload=lambda: None, is_loaded=lambda: True)
    coordinator.register("b", unload=lambda: None, is_loaded=lambda: False)
    assert coordinator.loaded_runtimes() == ["a"]


def test_voxcpm_provider_registers_with_global_coordinator():
    provider = VoxCpmProvider(runtime_client=None)
    try:
        assert speech_runtime_coordinator.runtimes["voxcpm2"].owner == "voxcpm2"
        assert "voxcpm2" not in speech_runtime_coordinator.loaded_runtimes()
        provider._loaded_model_id = "openbmb/VoxCPM2"
        assert "voxcpm2" in speech_runtime_coordinator.loaded_runtimes()
    finally:
        speech_runtime_coordinator.unregister("voxcpm2")


@pytest.mark.asyncio
async def test_voxcpm_synthesis_fails_explicitly_when_other_runtime_cannot_unload():
    """No silent fallback: a failed cross-runtime unload surfaces as an
    explicit VOXCPM_RUNTIME_BUSY provider error."""
    from app.services.speech_runtime_coordinator import SpeechRuntimeCoordinator
    import app.providers.voxcpm_provider as provider_module

    provider = VoxCpmProvider(runtime_client=None)
    broken_coordinator = SpeechRuntimeCoordinator()

    async def failing_unload():
        raise RuntimeError("cannot unload")

    broken_coordinator.register(
        "vieneu-heavy", unload=failing_unload, is_loaded=lambda: True
    )
    broken_coordinator.register(
        "voxcpm2",
        unload=provider.unload_model,
        is_loaded=lambda: provider._loaded_model_id is not None,
    )
    original = provider_module.speech_runtime_coordinator
    try:
        provider_module.speech_runtime_coordinator = broken_coordinator
        from app.services.voxcpm_runtime import VoxCpmSynthesisRequest

        with pytest.raises(VoxCpmProviderError) as exc_info:
            await provider._synthesize_with_runtime(
                VoxCpmSynthesisRequest(
                    text="xin chào", output_path="out.wav", reference_wav_path="ref.wav"
                ),
                model_id="openbmb/VoxCPM2",
            )
        assert exc_info.value.code == "VOXCPM_RUNTIME_BUSY"
    finally:
        provider_module.speech_runtime_coordinator = original
        speech_runtime_coordinator.unregister("voxcpm2")


@pytest.mark.asyncio
async def test_unload_model_reliable_with_dead_client():
    """Model unload must be reliable even when the worker client is gone."""

    class DeadClient:
        async def unload_model(self):
            raise RuntimeError("worker already dead")

    provider = VoxCpmProvider(runtime_client=None)
    provider._runtime = DeadClient()
    provider._loaded_model_id = "openbmb/VoxCPM2"

    # unload swallows the dead-client error and resets state regardless
    result = await provider.unload_model()
    assert provider._loaded_model_id is None
    assert provider._runtime is None
    assert result["released"] is True


@pytest.mark.asyncio
async def test_unload_model_when_not_running_is_noop():
    provider = VoxCpmProvider(runtime_client=None)
    result = await provider.unload_model()
    assert result == {"status": "not_running", "released": False}


@pytest.mark.asyncio
async def test_unload_before_load_happens_for_voxcpm_model_load():
    """Full provider flow: acquiring the VoxCPM2 runtime unloads a loaded
    competing runtime before the model load RPC is issued."""
    from app.config import settings
    import app.providers.voxcpm_provider as provider_module

    unloaded: list[str] = []
    provider = VoxCpmProvider(runtime_client=None)
    coord = SpeechRuntimeCoordinator()

    async def unload_other():
        unloaded.append("other")

    coord.register("other", unload=unload_other, is_loaded=lambda: True)
    coord.register(
        "voxcpm2",
        unload=provider.unload_model,
        is_loaded=lambda: provider._loaded_model_id is not None,
    )

    class FakeClient:
        is_running = False
        load_calls: list = []

        async def load_model(self, model_id="openbmb/VoxCPM2", device="auto"):
            self.load_calls.append((model_id, device))
            return {"status": "loaded"}

        async def synthesize(self, request, *, method="synthesize_emotional", timeout_seconds=None):
            from app.services.voxcpm_runtime import VoxCpmSynthesisResult

            return VoxCpmSynthesisResult(
                output_path=request.output_path,
                sample_rate=48000,
                duration_seconds=0.1,
                backend="real",
                method=method,
            )

    fake_client = FakeClient()
    provider._runtime = fake_client
    original = provider_module.speech_runtime_coordinator
    original_timeout = settings.voxcpm_inference_timeout_seconds
    try:
        provider_module.speech_runtime_coordinator = coord
        from app.services.voxcpm_runtime import VoxCpmSynthesisRequest

        await provider._synthesize_with_runtime(
            VoxCpmSynthesisRequest(
                text="hi", output_path="out.wav", reference_wav_path="ref.wav"
            ),
            model_id="openbmb/VoxCPM2",
        )
        assert unloaded == ["other"]
        assert fake_client.load_calls == [("openbmb/VoxCPM2", "auto")]
        assert provider._loaded_model_id == "openbmb/VoxCPM2"
    finally:
        provider_module.speech_runtime_coordinator = original
        settings.voxcpm_inference_timeout_seconds = original_timeout
        speech_runtime_coordinator.unregister("voxcpm2")