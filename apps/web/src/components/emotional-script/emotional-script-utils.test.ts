import { describe, expect, it } from "vitest"
import { countDeliveryTags, createQuickScriptDocument } from "./emotional-script-utils"

describe("emotional script utilities", () => {
  it("counts native and approximated tags without treating the tag text as prose", () => {
    const result = countDeliveryTags("[cười] Xin chào. [sợ hãi] Đừng đi! [thì thầm] Im nào.")

    expect(result.total).toBe(3)
    expect(result.native).toBe(1)
    expect(result.approximated).toBe(1)
    expect(result.unsupported).toBe(1)
  })

  it("creates a quick document with one assigned default voice", () => {
    const document = createQuickScriptDocument("Một câu chuyện.", "Minh Đức")

    expect(document.defaults.voice_id).toBe("Minh Đức")
    expect(document.scenes[0].lines[0].text).toBe("Một câu chuyện.")
    expect(document.scenes[0].lines[0].id).toBe("line-1-1")
  })
})

