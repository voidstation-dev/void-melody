from app.services.script_parser import parse_script


def test_parse_dialogue_and_delivery_tags_into_stable_document():
    content = """[Cảnh 1]
Linh: [sợ hãi] Anh có nghe thấy gì không?
Nam: [bình tĩnh] Không sao đâu.
Người dẫn: [cười] Rồi cả hai cùng im lặng.
"""

    document = parse_script(content, format="dialogue_txt")

    assert document.scenes[0].title == "Cảnh 1"
    assert [speaker.name for speaker in document.speakers] == [
        "Linh",
        "Nam",
        "Người dẫn",
    ]
    assert document.scenes[0].lines[0].text == "Anh có nghe thấy gì không?"
    assert document.scenes[0].lines[0].delivery.intent == "fear"
    assert document.scenes[0].lines[2].delivery.nonverbals == ["laugh"]
    assert document.scenes[0].lines[0].id == "line-1-1"

    again = parse_script(content, format="dialogue_txt")
    assert again.model_dump(mode="json") == document.model_dump(mode="json")


def test_parse_unknown_tags_without_leaking_bracket_text_to_synthesis():
    document = parse_script("[hoảng loạn cực độ] Đừng đến đây!", format="plain")

    assert document.scenes[0].lines[0].text == "Đừng đến đây!"
    assert document.warnings[0].code == "UNKNOWN_DELIVERY_TAG"
    assert document.warnings[0].value == "hoảng loạn cực độ"


def test_parse_srt_preserves_source_timing_and_multiline_text():
    content = """1
00:00:01,000 --> 00:00:04,250
Linh: [thở dài] Anh về rồi.

2
00:00:05,000 --> 00:00:07,000
Người dẫn: Căn phòng lại im ắng.
"""

    document = parse_script(content, format="srt")

    first = document.scenes[0].lines[0]
    assert first.source_timing is not None
    assert first.source_timing.start_ms == 1000
    assert first.source_timing.end_ms == 4250
    assert first.delivery.nonverbals == ["sigh"]
    assert document.scenes[0].lines[1].speaker_id is not None

