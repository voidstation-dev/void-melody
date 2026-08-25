from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.base import ProviderResult
from app.providers.vieneu_provider import VieneuProvider


@pytest.fixture
def mock_model_manager():
    with patch("app.providers.vieneu_provider.ModelManager") as MockModelManager:
        mock_manager = MockModelManager.return_value

        mock_engine = MagicMock()
        mock_engine.infer = MagicMock(return_value=b"fake_wav_data")
        mock_engine.save = MagicMock()

        mock_manager.get_engine = AsyncMock(return_value=mock_engine)
        yield mock_manager, mock_engine


@pytest.mark.asyncio
async def test_vieneu_provider_synthesize(mock_model_manager):
    _mock_manager, mock_engine = mock_model_manager
    provider = VieneuProvider()

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_exec.return_value = mock_process

        result = await provider.synthesize(
            text="hello",
            voice_type="test_voice",
            resource_id=None,
            rate=1.0,
        )

        assert isinstance(result, ProviderResult)
        assert result.local_paths is not None
        assert len(result.local_paths) == 1
        assert result.local_paths[0].endswith(".wav")
        assert result.raw_response["engine"] == "vieneu-v3-turbo"
        assert result.raw_response["voice"] == "test_voice"
        assert result.raw_response["lossless"] is True

        # Verify infer was called
        mock_engine.infer.assert_called_once_with(
            text="hello",
            voice="test_voice",
            ref_audio=None,
            prompt_text=None,
            style="tu_nhien",
            apply_watermark=False,
        )


@pytest.mark.asyncio
async def test_vieneu_provider_synthesize_prepared_voice_zero_re_enrollment(mock_model_manager):
    import numpy as np
    from app.services.prepared_voice import PreparedVoice

    _mock_manager, mock_engine = mock_model_manager
    provider = VieneuProvider()

    dummy_emb = np.zeros(192, dtype=np.float32)
    dummy_codes = np.zeros((1, 30), dtype=np.int32)
    prepared = PreparedVoice(
        voice_type="custom-v2-id",
        provider_id="vieneu",
        source="custom",
        voice_revision="v2",
        speaker_emb=dummy_emb,
        ref_codes=dummy_codes,
        clone_mode="fidelity",
        profile_format_version="vieneu-enrollment-v2",
        reference_audio_path="/path/to/reference.wav",
        prompt_text="Prompt text",
    )

    result = await provider.synthesize(
        text="Xin chào",
        voice_type="custom-v2-id",
        prepared_voice=prepared,
    )

    assert result.local_paths[0].endswith(".wav")
    mock_engine.infer.assert_called_once_with(
        text="Xin chào",
        voice={"speaker_emb": dummy_emb, "codes": dummy_codes},
        ref_audio=None,
        prompt_text="Prompt text",
        style="tu_nhien",
        apply_watermark=False,
        use_ref_codes=True,
    )
    assert getattr(mock_engine, "prepare_reference", None) is None or mock_engine.prepare_reference.call_count == 0

