import { afterEach, describe, expect, it, vi } from "vitest"

import {
  apiFetch,
  apiFetchBlob,
  onTrialBlocked,
  setApiConnection,
} from "./api-client"


describe("authenticated API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setApiConnection("http://localhost:8000", null)
  })

  it("attaches the Melody token to JSON requests", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    )
    vi.stubGlobal("fetch", fetchMock)
    setApiConnection("http://127.0.0.1:43210", "secret-token")

    await apiFetch("/api/v1/voices")

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:43210/api/v1/voices",
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-Melody-Token": "secret-token",
        }),
      }),
    )
  })

  it("attaches the token when fetching media blobs", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(new Blob(["audio"]), { status: 200 }),
    )
    vi.stubGlobal("fetch", fetchMock)
    setApiConnection("http://127.0.0.1:43210", "secret-token")

    const blob = await apiFetchBlob("/api/v1/tts/jobs/job-1/audio")

    expect(blob.size).toBe(5)
    expect(fetchMock.mock.calls[0][1].headers).toEqual(
      expect.objectContaining({ "X-Melody-Token": "secret-token" }),
    )
  })

  it("does not override the browser boundary for multipart uploads", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    )
    vi.stubGlobal("fetch", fetchMock)
    const body = new FormData()
    body.append("audio_file", new File(["audio"], "sample.wav", { type: "audio/wav" }))

    await apiFetch("/api/v1/tts/voices/analyze", { method: "POST", body })

    expect(fetchMock.mock.calls[0][1].headers).not.toHaveProperty("Content-Type")
    expect(fetchMock.mock.calls[0][1].body).toBe(body)
  })

  it("notifies the trial context when the backend rejects new compute", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ code: "TRIAL_EXPIRED", detail: { code: "TRIAL_EXPIRED" } }), { status: 403 }),
    )
    vi.stubGlobal("fetch", fetchMock)
    const listener = vi.fn()
    const unsubscribe = onTrialBlocked(listener)

    await expect(apiFetch("/api/v1/tts/jobs", { method: "POST", body: "{}" })).rejects.toThrow()

    expect(listener).toHaveBeenCalledOnce()
    unsubscribe()
  })
})
