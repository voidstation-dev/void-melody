import test from "node:test"
import assert from "node:assert/strict"

import { assertSidecarFresh } from "./sync-tauri-dev-binaries.mjs"

test("rejects a sidecar built from a different source revision", () => {
  assert.throws(
    () => assertSidecarFresh({ source_revision: "4cb8ff5" }, "de68cf5"),
    /stale API sidecar/i,
  )
})

test("accepts a sidecar built from the current source revision", () => {
  assert.doesNotThrow(() =>
    assertSidecarFresh({ source_revision: "de68cf5" }, "de68cf5"),
  )
})
