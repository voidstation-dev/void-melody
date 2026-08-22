"""Public contracts for the VieNeu-only Emotional Script workflow."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DeliveryIntent(str, Enum):
    NEUTRAL = "neutral"
    CALM = "calm"
    JOY = "joy"
    SAD = "sad"
    FEAR = "fear"
    ANGER = "anger"
    SURPRISE = "surprise"
    TENSION = "tension"
    MYSTERIOUS = "mysterious"
    NARRATION = "narration"
    SHOUT = "shout"
    WHISPER = "whisper"


class NonVerbalEvent(str, Enum):
    LAUGH = "laugh"
    SIGH = "sigh"
    CLEAR_THROAT = "clear_throat"


class ScriptSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["quick_text", "plain", "dialogue_txt", "srt", "import"] = "quick_text"
    original_name: str | None = None


class ScriptDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    voice_id: str | None = None
    global_delivery_prompt: str | None = None
    base_rate: float = Field(default=1.0, ge=0.5, le=2.0)
    pause_profile: Literal["short", "normal", "long"] = "normal"


class SourceTiming(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)


class DeliveryInstruction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: DeliveryIntent = DeliveryIntent.NEUTRAL
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    nonverbals: list[NonVerbalEvent] = Field(default_factory=list)
    pause_before_ms: int = Field(default=0, ge=0, le=60_000)
    pause_after_ms: int = Field(default=0, ge=0, le=60_000)


class ScriptLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    order: int = Field(ge=0)
    speaker_id: str | None = None
    text: str = Field(min_length=1)
    delivery: DeliveryInstruction = Field(default_factory=DeliveryInstruction)
    source_timing: SourceTiming | None = None


class ScriptScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    order: int = Field(ge=0)
    lines: list[ScriptLine] = Field(default_factory=list)


class ScriptSpeaker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    voice_id: str | None = None


class ScriptWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    value: str | None = None
    line_id: str | None = None


class EmotionalScriptDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(default=1, ge=1)
    id: str = ""
    title: str = "Kịch bản chưa đặt tên"
    revision: int = Field(default=1, ge=1)
    source: ScriptSource = Field(default_factory=ScriptSource)
    defaults: ScriptDefaults = Field(default_factory=ScriptDefaults)
    speakers: list[ScriptSpeaker] = Field(default_factory=list)
    scenes: list[ScriptScene] = Field(default_factory=list)
    warnings: list[ScriptWarning] = Field(default_factory=list)

    @property
    def lines(self) -> list[ScriptLine]:
        return [line for scene in self.scenes for line in scene.lines]


ScriptStatus = Literal["NEVER_RENDERED", "READY", "STALE", "RENDERING", "FAILED"]
RenderScope = Literal["all", "stale", "failed", "selected"]
RenderStatus = Literal[
    "queued",
    "planning",
    "rendering",
    "mixing",
    "completed",
    "partial_failed",
    "failed",
    "cancelled",
    "interrupted",
]
SegmentStatus = Literal["pending", "queued", "rendering", "ready", "failed", "cancelled", "reused"]
VoiceMode = Literal["PRESET", "CLONE"]

