import pytest

from app.providers.base import ProviderResult
from app.schemas.emotional_script import DeliveryInstruction, ScriptLine
from app.services.vieneu_delivery_resolver import resolve_vieneu_delivery
from app.services.vieneu_script_synthesis import VieNeuScriptSynthesisAdapter


@pytest.mark.asyncio
async def test_script_adapter_passes_resolved_text_without_deprecated_style():
    calls: list[dict[str, object]] = []

    class FakeProvider:
        async def synthesize_script(self, **kwargs):
            calls.append(kwargs)
            return ProviderResult(raw_response={}, audio_urls=[], local_paths=["/tmp/fake.mp3"])

    resolved = resolve_vieneu_delivery(
        ScriptLine(id="line-1-1", order=0, text="Xin chào.", delivery=DeliveryInstruction()),
        voice_id="Minh Đức",
        voice_mode="PRESET",
    )
    result = await VieNeuScriptSynthesisAdapter(provider=FakeProvider()).synthesize(resolved)

    assert result.local_paths == ["/tmp/fake.mp3"]
    assert calls[0]["text"] == "Xin chào."
    assert "style" not in calls[0]

