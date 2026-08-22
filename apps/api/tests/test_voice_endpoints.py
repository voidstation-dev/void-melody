from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.providers.base import ProviderVoice
from app.services.voice_catalog import voice_catalog


@pytest.mark.asyncio
async def test_voice_list_can_filter_provider_before_pagination():
    catalog_voices = [
        ProviderVoice(
            language_short="vi",
            language_code="vi-VN",
            voice_type="capcut-voice",
            display_name="CapCut voice",
            provider_id="capcut",
        ),
        ProviderVoice(
            language_short="vi",
            language_code="vi-VN",
            voice_type="vieneu-voice",
            display_name="VieNeu voice",
            provider_id="vieneu",
        ),
    ]

    with patch.object(voice_catalog, "list_voices", return_value=catalog_voices):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/v1/voices?provider_id=vieneu&page_size=1"
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [voice["voiceType"] for voice in payload["items"]] == ["vieneu-voice"]
