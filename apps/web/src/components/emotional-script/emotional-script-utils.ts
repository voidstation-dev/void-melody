import type { DeliveryIntent, NonVerbalEvent, ScriptDocument } from "@/types/emotional-script"

const nativeTags: Record<string, NonVerbalEvent> = {
  cười: "laugh",
  "thở dài": "sigh",
  "hắng giọng": "clear_throat",
}

const approximatedTags: Record<string, DeliveryIntent> = {
  "bình tĩnh": "calm",
  vui: "joy",
  buồn: "sad",
  "sợ hãi": "fear",
  "tức giận": "anger",
  "bất ngờ": "surprise",
  "căng thẳng": "tension",
  "bí ẩn": "mysterious",
  "kể chuyện": "narration",
  "gầm lên": "shout",
}

export function countDeliveryTags(text: string) {
  const tags = [...text.matchAll(/\[([^\]]+)\]/g)].map((match) => match[1].trim().toLocaleLowerCase())
  return {
    total: tags.length,
    native: tags.filter((tag) => nativeTags[tag]).length,
    approximated: tags.filter((tag) => approximatedTags[tag]).length,
    unsupported: tags.filter((tag) => tag === "thì thầm").length,
  }
}

export function createQuickScriptDocument(text: string, voiceId: string): ScriptDocument {
  return {
    version: 1,
    title: "Kịch bản chưa đặt tên",
    revision: 1,
    source: { type: "quick_text", original_name: null },
    defaults: { voice_id: voiceId || null, global_delivery_prompt: null, base_rate: 1, pause_profile: "normal" },
    speakers: [],
    scenes: [{
      id: "scene-1",
      title: "Cảnh 1",
      order: 0,
      lines: [{
        id: "line-1-1",
        order: 0,
        speaker_id: null,
        text: text.trim(),
        delivery: { intent: "neutral", intensity: 0.5, nonverbals: [], pause_before_ms: 0, pause_after_ms: 0 },
        source_timing: null,
      }],
    }],
    warnings: [],
  }
}

