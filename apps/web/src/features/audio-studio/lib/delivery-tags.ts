import type { DeliveryTag } from "../types"

export const NATIVE_CUES: DeliveryTag[] = [
  {
    id: "laugh",
    label: "Cười",
    type: "native",
    token: "[cười]",
    icon: "😄",
    engine: ["vieneu"],
    description: "Âm thanh cười tự nhiên được VieNeu AI hỗ trợ trực tiếp.",
    colorVariant: "green",
  },
  {
    id: "sigh",
    label: "Thở dài",
    type: "native",
    token: "[thở dài]",
    icon: "😮‍💨",
    engine: ["vieneu"],
    description: "Tiếng thở dài giải tỏa cảm xúc.",
    colorVariant: "green",
  },
  {
    id: "clear_throat",
    label: "Hắng giọng",
    type: "native",
    token: "[hắng giọng]",
    icon: "🗣️",
    engine: ["vieneu"],
    description: "Tiếng hắng giọng / e hèm chuẩn bị nói.",
    colorVariant: "green",
  },
]

export const EMOTION_TAGS: DeliveryTag[] = [
  {
    id: "calm",
    label: "Bình tĩnh",
    type: "emotion",
    token: "[bình tĩnh]",
    icon: "🧘",
    description: "Giọng điệu điềm đạm, khoan thai.",
    colorVariant: "amber",
  },
  {
    id: "joy",
    label: "Vui vẻ",
    type: "emotion",
    token: "[vui]",
    icon: "✨",
    description: "Giọng hào hứng, tươi vui và tích cực.",
    colorVariant: "amber",
  },
  {
    id: "sad",
    label: "Buồn bã",
    type: "emotion",
    token: "[buồn]",
    icon: "💧",
    description: "Âm trầm, xúc động, ngậm ngùi.",
    colorVariant: "amber",
  },
  {
    id: "fear",
    label: "Sợ hãi",
    type: "emotion",
    token: "[sợ hãi]",
    icon: "😨",
    description: "Giọng run rẩy, dồn dập, lo lắng.",
    colorVariant: "amber",
  },
  {
    id: "anger",
    label: "Tức giận",
    type: "emotion",
    token: "[tức giận]",
    icon: "🔥",
    description: "Âm lượng mạnh mẽ, dứt khoát, gay gắt.",
    colorVariant: "amber",
  },
  {
    id: "surprise",
    label: "Bất ngờ",
    type: "emotion",
    token: "[bất ngờ]",
    icon: "⚡",
    description: "Giọng ngạc nhiên, thảng thốt.",
    colorVariant: "amber",
  },
  {
    id: "tension",
    label: "Căng thẳng",
    type: "emotion",
    token: "[căng thẳng]",
    icon: "⏱️",
    description: "Không khí hồi hộp, nghẹt thở.",
    colorVariant: "amber",
  },
  {
    id: "mysterious",
    label: "Bí ẩn",
    type: "emotion",
    token: "[bí ẩn]",
    icon: "🌙",
    description: "Giọng thì thào, gợi sự tò mò.",
    colorVariant: "amber",
  },
  {
    id: "narration",
    label: "Kể chuyện",
    type: "emotion",
    token: "[kể chuyện]",
    icon: "📖",
    description: "Giọng truyền cảm, dẫn chuyện cuốn hút.",
    colorVariant: "amber",
  },
]

export const ADVANCED_DELIVERY_TAGS: DeliveryTag[] = [
  {
    id: "slow",
    label: "Chậm rãi",
    type: "delivery",
    token: "[chậm]",
    icon: "🐢",
    description: "Giảm tốc độ đọc cho câu này.",
    colorVariant: "blue",
  },
  {
    id: "fast",
    label: "Nhanh",
    type: "delivery",
    token: "[nhanh]",
    icon: "🐇",
    description: "Tăng tốc độ đọc cho câu này.",
    colorVariant: "blue",
  },
  {
    id: "short_pause",
    label: "Ngắt ngắn",
    type: "delivery",
    token: "[ngắt ngắn]",
    icon: "⏸️",
    description: "Tạm dừng nhẹ (khoảng 300ms).",
    colorVariant: "blue",
  },
  {
    id: "long_pause",
    label: "Ngắt dài",
    type: "delivery",
    token: "[ngắt dài]",
    icon: "🛑",
    description: "Tạm dừng rõ ràng giữa 2 ý (khoảng 800ms).",
    colorVariant: "blue",
  },
  {
    id: "emphasize",
    label: "Nhấn mạnh",
    type: "delivery",
    token: "[nhấn mạnh]",
    icon: "🎯",
    description: "Tăng trọng âm và độ nhấn cho từ/cụm từ.",
    colorVariant: "blue",
  },
  {
    id: "gentle",
    label: "Nhẹ nhàng",
    type: "delivery",
    token: "[nhẹ nhàng]",
    icon: "🌸",
    description: "Phát âm êm dịu, ấm áp.",
    colorVariant: "blue",
  },
  {
    id: "whisper",
    label: "Thì thầm",
    type: "delivery",
    token: "[thì thầm]",
    icon: "🤫",
    description: "Giọng thì thầm nhỏ nhẹ.",
    colorVariant: "blue",
  },
]

export const ALL_TAGS = [...NATIVE_CUES, ...EMOTION_TAGS, ...ADVANCED_DELIVERY_TAGS]

export const TAG_LOOKUP = new Map<string, DeliveryTag>(
  ALL_TAGS.map((tag) => [tag.token.toLowerCase(), tag]),
)

export function findTagByToken(token: string): DeliveryTag | undefined {
  const normalized = token.trim().toLowerCase()
  const withBrackets = normalized.startsWith("[") && normalized.endsWith("]") ? normalized : `[${normalized}]`
  return TAG_LOOKUP.get(withBrackets)
}
