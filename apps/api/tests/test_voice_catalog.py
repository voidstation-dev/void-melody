import os
from pathlib import Path
from unittest.mock import patch

from app.services.voice_catalog import VoiceCatalog


def test_voice_catalog_reads_file_once_until_modification_time_changes(
    tmp_path: Path,
):
    catalog_path = tmp_path / "Voice.json"
    catalog_path.write_text(
        '[{"lan":"vi","lang":"vi-VN","voice_type":"voice-1",'
        '"display_name":"First","resource_id":"resource-1"}]',
        encoding="utf-8",
    )
    catalog = VoiceCatalog(catalog_path)

    original_read_text = Path.read_text
    reads = 0

    def counted_read_text(path, *args, **kwargs):
        nonlocal reads
        reads += 1
        return original_read_text(path, *args, **kwargs)

    with (
        patch.object(Path, "read_text", counted_read_text),
        patch("app.services.voice_catalog.list_vieneu_preset_voices", return_value=()),
    ):
        assert catalog.get_voice("voice-1").display_name == "First"
        assert catalog.list_voices("vi-VN")[0].voice_type == "voice-1"
        assert reads == 1

        catalog_path.write_text(
            '[{"lan":"vi","lang":"vi-VN","voice_type":"voice-2",'
            '"display_name":"Second","resource_id":"resource-2"}]',
            encoding="utf-8",
        )
        stat = catalog_path.stat()
        os.utime(
            catalog_path,
            ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000),
        )

        assert catalog.get_voice("voice-1") is None
        assert catalog.get_voice("voice-2").display_name == "Second"
        assert reads == 2


def test_voice_catalog_includes_all_vieneu_preset_voices_with_metadata(tmp_path: Path):
    catalog_path = tmp_path / "Voice.json"
    catalog_path.write_text("[]", encoding="utf-8")
    catalog = VoiceCatalog(catalog_path)

    vieneu_voices = [
        voice for voice in catalog.list_voices() if voice.provider_id == "vieneu"
    ]

    assert len(vieneu_voices) == 14
    assert {voice.display_name for voice in vieneu_voices} >= {
        "Minh Đức",
        "Trúc Ly",
        "Thái Sơn",
        "Xuân Vĩnh",
    }
    thai_son = next(voice for voice in vieneu_voices if voice.display_name == "Thái Sơn")
    assert thai_son.gender == "male"
    assert thai_son.region == "Nam"
    assert thai_son.style == "doc_truyen"
