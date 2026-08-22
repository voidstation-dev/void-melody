"""Deterministic TXT/SRT parser for Emotional Script documents."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.emotional_script import (
    DeliveryIntent,
    DeliveryInstruction,
    EmotionalScriptDocument,
    NonVerbalEvent,
    ScriptLine,
    ScriptScene,
    ScriptSource,
    ScriptSpeaker,
    ScriptWarning,
    SourceTiming,
)

_TAG_RE = re.compile(r"\[([^\[\]\n]+)\]")
_SPEAKER_RE = re.compile(r"^([^:\n]{1,80}):\s*(.*)$")
_SCENE_RE = re.compile(r"^(?:#\s*|\[)(cảnh\s+[^\]]+|scene\s+[^\]]+)(?:\])?\s*$", re.I)
_SRT_TIME_RE = re.compile(
    r"^(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2})[,.](\d{3})$"
)
_SRT_CLOCK_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2})[,.](\d{3})$")

_ALIASES: dict[str, tuple[str, str]] = {
    "bình thường": ("intent", DeliveryIntent.NEUTRAL.value),
    "neutral": ("intent", DeliveryIntent.NEUTRAL.value),
    "calm": ("intent", DeliveryIntent.CALM.value),
    "bình tĩnh": ("intent", DeliveryIntent.CALM.value),
    "joy": ("intent", DeliveryIntent.JOY.value),
    "vui": ("intent", DeliveryIntent.JOY.value),
    "sad": ("intent", DeliveryIntent.SAD.value),
    "buồn": ("intent", DeliveryIntent.SAD.value),
    "fear": ("intent", DeliveryIntent.FEAR.value),
    "sợ hãi": ("intent", DeliveryIntent.FEAR.value),
    "anger": ("intent", DeliveryIntent.ANGER.value),
    "tức giận": ("intent", DeliveryIntent.ANGER.value),
    "surprise": ("intent", DeliveryIntent.SURPRISE.value),
    "bất ngờ": ("intent", DeliveryIntent.SURPRISE.value),
    "tension": ("intent", DeliveryIntent.TENSION.value),
    "căng thẳng": ("intent", DeliveryIntent.TENSION.value),
    "mysterious": ("intent", DeliveryIntent.MYSTERIOUS.value),
    "bí ẩn": ("intent", DeliveryIntent.MYSTERIOUS.value),
    "narration": ("intent", DeliveryIntent.NARRATION.value),
    "kể chuyện": ("intent", DeliveryIntent.NARRATION.value),
    "shout": ("intent", DeliveryIntent.SHOUT.value),
    "gầm lên": ("intent", DeliveryIntent.SHOUT.value),
    "whisper": ("intent", DeliveryIntent.WHISPER.value),
    "thì thầm": ("intent", DeliveryIntent.WHISPER.value),
    "laugh": ("nonverbal", NonVerbalEvent.LAUGH.value),
    "chuckle": ("nonverbal", NonVerbalEvent.LAUGH.value),
    "cười": ("nonverbal", NonVerbalEvent.LAUGH.value),
    "sigh": ("nonverbal", NonVerbalEvent.SIGH.value),
    "thở dài": ("nonverbal", NonVerbalEvent.SIGH.value),
    "clear throat": ("nonverbal", NonVerbalEvent.CLEAR_THROAT.value),
    "hắng giọng": ("nonverbal", NonVerbalEvent.CLEAR_THROAT.value),
}


@dataclass
class _ParsedLine:
    text: str
    speaker_name: str | None
    delivery: DeliveryInstruction
    timing: SourceTiming | None = None


def _time_to_ms(value: str) -> int:
    match = _SRT_CLOCK_RE.match(value)
    if not match:
        raise ValueError(value)
    hours, minutes, seconds, millis = (int(item) for item in match.groups()[:4])
    return (((hours * 60) + minutes) * 60 + seconds) * 1000 + millis


def _parse_inline(text: str, *, warning_line_id: str | None = None) -> tuple[str, DeliveryInstruction, list[ScriptWarning]]:
    intent = DeliveryIntent.NEUTRAL
    nonverbals: list[NonVerbalEvent] = []
    warnings: list[ScriptWarning] = []

    def replace_tag(match: re.Match[str]) -> str:
        nonlocal intent
        raw = match.group(1).strip()
        key = raw.casefold()
        mapped = _ALIASES.get(key)
        if mapped is None:
            warnings.append(
                ScriptWarning(
                    code="UNKNOWN_DELIVERY_TAG",
                    message=f"Tag chưa được nhận diện: [{raw}]",
                    value=raw,
                    line_id=warning_line_id,
                )
            )
            return ""
        kind, value = mapped
        if kind == "intent":
            intent = DeliveryIntent(value)
        else:
            event = NonVerbalEvent(value)
            if event not in nonverbals:
                nonverbals.append(event)
        return ""

    cleaned = _TAG_RE.sub(replace_tag, text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned, DeliveryInstruction(intent=intent, nonverbals=nonverbals), warnings


def _speaker_id(name: str, known: dict[str, ScriptSpeaker]) -> str:
    normalized = " ".join(name.split())
    if normalized not in known:
        speaker_id = f"speaker-{len(known) + 1}"
        known[normalized] = ScriptSpeaker(id=speaker_id, name=normalized)
    return known[normalized].id


def _parse_content_lines(lines: list[_ParsedLine | str]) -> tuple[list[ScriptScene], list[ScriptSpeaker], list[ScriptWarning]]:
    speakers: dict[str, ScriptSpeaker] = {}
    warnings: list[ScriptWarning] = []
    scenes: list[ScriptScene] = []
    current = ScriptScene(id="scene-1", title="Cảnh 1", order=0, lines=[])
    scenes.append(current)

    for item in lines:
        if isinstance(item, str):
            raw = item.strip()
            if not raw:
                continue
            scene_match = _SCENE_RE.match(raw)
            if scene_match:
                title = scene_match.group(1).strip().rstrip("]")
                current = ScriptScene(
                    id=f"scene-{len(scenes) + 1}",
                    title=title[0].upper() + title[1:],
                    order=len(scenes),
                    lines=[],
                )
                scenes.append(current)
                continue
            speaker_name = None
            text = raw
            match = _SPEAKER_RE.match(raw)
            if match and match.group(1).strip():
                speaker_name = match.group(1).strip()
                text = match.group(2).strip()
            line_id = f"line-{current.order + 1}-{len(current.lines) + 1}"
            cleaned, delivery, line_warnings = _parse_inline(text, warning_line_id=line_id)
            warnings.extend(line_warnings)
            if cleaned:
                current.lines.append(
                    ScriptLine(
                        id=line_id,
                        order=len(current.lines),
                        speaker_id=_speaker_id(speaker_name, speakers) if speaker_name else None,
                        text=cleaned,
                        delivery=delivery,
                    )
                )
            continue

        line_id = f"line-{current.order + 1}-{len(current.lines) + 1}"
        cleaned, delivery, line_warnings = _parse_inline(item.text, warning_line_id=line_id)
        warnings.extend(line_warnings)
        if not cleaned:
            continue
        current.lines.append(
            ScriptLine(
                id=line_id,
                order=len(current.lines),
                speaker_id=_speaker_id(item.speaker_name, speakers) if item.speaker_name else None,
                text=cleaned,
                delivery=delivery,
                source_timing=item.timing,
            )
        )

    scenes = [scene for scene in scenes if scene.lines]
    for scene_order, scene in enumerate(scenes):
        scene.order = scene_order
        scene.id = f"scene-{scene_order + 1}"
        for line_order, line in enumerate(scene.lines):
            line.order = line_order
            line.id = f"line-{scene_order + 1}-{line_order + 1}"
    return scenes, list(speakers.values()), warnings


def _parse_srt(content: str) -> list[_ParsedLine | str]:
    result: list[_ParsedLine | str] = []
    blocks = re.split(r"\n\s*\n", content.replace("\r\n", "\n").strip())
    for block in blocks:
        rows = [row.strip() for row in block.split("\n") if row.strip()]
        if not rows:
            continue
        time_row_index = next((index for index, row in enumerate(rows) if "-->" in row), None)
        if time_row_index is None or time_row_index + 1 >= len(rows):
            result.append(" ".join(rows))
            continue
        try:
            start_raw, end_raw = (item.strip() for item in rows[time_row_index].split("-->", 1))
            timing = SourceTiming(start_ms=_time_to_ms(start_raw), end_ms=_time_to_ms(end_raw))
        except (ValueError, TypeError):
            result.append(" ".join(rows[time_row_index + 1 :]))
            continue
        subtitle_text = " ".join(rows[time_row_index + 1 :])
        speaker_match = _SPEAKER_RE.match(subtitle_text)
        speaker_name = speaker_match.group(1).strip() if speaker_match else None
        if speaker_match:
            subtitle_text = speaker_match.group(2).strip()
        result.append(
            _ParsedLine(
                text=subtitle_text,
                speaker_name=speaker_name,
                delivery=DeliveryInstruction(),
                timing=timing,
            )
        )
    return result


def parse_script(content: str, *, format: str = "auto", title: str | None = None, original_name: str | None = None) -> EmotionalScriptDocument:
    normalized = content.replace("\ufeff", "").replace("\r\n", "\n").strip()
    if not normalized:
        return EmotionalScriptDocument(
            title=title or "Kịch bản chưa đặt tên",
            source=ScriptSource(type="plain", original_name=original_name),
            scenes=[],
        )

    selected_format = format
    if selected_format == "auto":
        selected_format = "srt" if re.search(r"\d{2}:\d{2}:\d{2}[,.]\d{3}\s+-->", normalized) else "dialogue_txt" if any(_SPEAKER_RE.match(line) for line in normalized.split("\n") if line.strip()) else "plain"

    if selected_format == "srt":
        raw_lines = _parse_srt(normalized)
    else:
        raw_lines = normalized.split("\n")

    scenes, speakers, warnings = _parse_content_lines(raw_lines)
    return EmotionalScriptDocument(
        title=title or original_name or "Kịch bản chưa đặt tên",
        source=ScriptSource(type=selected_format if selected_format in {"plain", "dialogue_txt", "srt"} else "import", original_name=original_name),
        speakers=speakers,
        scenes=scenes,
        warnings=warnings,
    )
