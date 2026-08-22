// @vitest-environment jsdom

import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TauriProvider, useTauri } from "./tauri-provider";

const bridge = vi.hoisted(() => ({
  invoke: vi.fn(),
  resolveResource: vi.fn(),
  setApiConnection: vi.fn(),
  sidecar: vi.fn(),
}));

vi.mock("@tauri-apps/api/path", () => ({
  resolveResource: bridge.resolveResource,
}));

vi.mock("@tauri-apps/api/core", () => ({
  invoke: bridge.invoke,
}));

vi.mock("@tauri-apps/plugin-shell", () => ({
  Command: { sidecar: bridge.sidecar },
}));

vi.mock("@/lib/api-client", () => ({
  setApiConnection: bridge.setApiConnection,
}));

type OutputHandler = (line: string) => void;
type ProcessEventHandler = (payload: unknown) => void;

function makeSidecar() {
  const stdoutHandlers: OutputHandler[] = [];
  const stderrHandlers: OutputHandler[] = [];
  const processEventHandlers: Record<"error" | "close", ProcessEventHandler[]> = {
    error: [],
    close: [],
  };
  const child = { kill: vi.fn().mockResolvedValue(undefined) };
  const command = {
    stdout: { on: vi.fn((_event: string, handler: OutputHandler) => stdoutHandlers.push(handler)) },
    stderr: { on: vi.fn((_event: string, handler: OutputHandler) => stderrHandlers.push(handler)) },
    on: vi.fn((event: "error" | "close", handler: ProcessEventHandler) => {
      processEventHandlers[event].push(handler);
      return command;
    }),
    spawn: vi.fn().mockResolvedValue(child),
  };

  return { child, command, stdoutHandlers, stderrHandlers, processEventHandlers };
}

function ContextProbe() {
  const { isDesktop, isReady, shutdownSidecar, restartSidecar } = useTauri();

  return (
    <div>
      <output>{isDesktop ? "desktop" : "browser"}:{isReady ? "ready" : "starting"}</output>
      <button onClick={() => void shutdownSidecar()}>Stop</button>
      <button onClick={() => void restartSidecar()}>Restart</button>
    </div>
  );
}

describe("TauriProvider", () => {
  beforeEach(() => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: undefined,
      writable: true,
    });
    bridge.invoke.mockResolvedValue({ data_dir: "/app-data", integrity_key: "trial-key" });
    bridge.resolveResource.mockImplementation(async (path: string) => `/resources/${path}`);
    bridge.setApiConnection.mockReset();
    bridge.sidecar.mockReset();
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "random-token") });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reports browser readiness without loading the desktop bridge", async () => {
    render(
      <TauriProvider>
        <ContextProbe />
      </TauriProvider>,
    );

    expect(await screen.findByText("browser:ready")).toBeInTheDocument();
    expect(bridge.sidecar).not.toHaveBeenCalled();
  });

  it("preserves authenticated random-port bootstrap and reports desktop readiness", async () => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", { value: {}, configurable: true });
    const sidecar = makeSidecar();
    bridge.sidecar.mockReturnValue(sidecar.command);

    render(
      <TauriProvider>
        <ContextProbe />
      </TauriProvider>,
    );

    await waitFor(() => expect(sidecar.command.spawn).toHaveBeenCalledOnce());
    expect(bridge.sidecar).toHaveBeenCalledWith("bin/melody-api", [], {
      env: expect.objectContaining({
        API_HOST: "127.0.0.1",
        API_PORT: "0",
        MELODY_API_TOKEN: "random-token",
        MELODY_DATA_DIR: "/app-data",
        MELODY_TRIAL_INTEGRITY_KEY: "trial-key",
      }),
    });
    expect(screen.queryByText("desktop:ready")).not.toBeInTheDocument();

    act(() => sidecar.stdoutHandlers[0]("Listening on http://127.0.0.1:43127"));

    expect(await screen.findByText("desktop:ready")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith("http://127.0.0.1:43127/api/v1/health/live", { method: "GET" });
    expect(bridge.setApiConnection).toHaveBeenCalledWith("http://127.0.0.1:43127", "random-token");
  });

  it("recognizes a Uvicorn port split across output chunks", async () => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", { value: {}, configurable: true });
    const sidecar = makeSidecar();
    bridge.sidecar.mockReturnValue(sidecar.command);

    render(
      <TauriProvider>
        <ContextProbe />
      </TauriProvider>,
    );

    await waitFor(() => expect(sidecar.command.spawn).toHaveBeenCalledOnce());
    act(() => {
      sidecar.stdoutHandlers[0]("Uvicorn running on http://127.0.0.1:");
      sidecar.stdoutHandlers[0]("43128 (Press CTRL+C to quit)");
    });

    expect(await screen.findByText("desktop:ready")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith("http://127.0.0.1:43128/api/v1/health/live", { method: "GET" });
  });

  it("awaits sidecar shutdown and can restart it with a fresh process", async () => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", { value: {}, configurable: true });
    const first = makeSidecar();
    const second = makeSidecar();
    bridge.sidecar.mockReturnValueOnce(first.command).mockReturnValueOnce(second.command);

    render(
      <TauriProvider>
        <ContextProbe />
      </TauriProvider>,
    );
    await waitFor(() => expect(first.command.spawn).toHaveBeenCalledOnce());
    act(() => first.stdoutHandlers[0]("Listening on 127.0.0.1:41001"));
    await screen.findByText("desktop:ready");

    fireEvent.click(screen.getByRole("button", { name: "Stop" }));
    await waitFor(() => expect(first.child.kill).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByRole("button", { name: "Restart" }));

    await waitFor(() => expect(second.command.spawn).toHaveBeenCalledOnce());
    act(() => second.stderrHandlers[0]("Server started at port 41002"));
    expect(await screen.findByText("desktop:ready")).toBeInTheDocument();
  });

  it("shows the existing startup error screen when the sidecar cannot spawn", async () => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", { value: {}, configurable: true });
    const sidecar = makeSidecar();
    sidecar.command.spawn.mockRejectedValue(new Error("sidecar unavailable"));
    bridge.sidecar.mockReturnValue(sidecar.command);

    render(
      <TauriProvider>
        <ContextProbe />
      </TauriProvider>,
    );

    expect(await screen.findByRole("heading", { name: "Failed to start local API" })).toBeInTheDocument();
    expect(screen.getByText("Error: sidecar unavailable")).toBeInTheDocument();
  });

  it("surfaces a sidecar process error without waiting for the startup timeout", async () => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", { value: {}, configurable: true });
    const sidecar = makeSidecar();
    bridge.sidecar.mockReturnValue(sidecar.command);

    render(
      <TauriProvider>
        <ContextProbe />
      </TauriProvider>,
    );

    await waitFor(() => expect(sidecar.command.spawn).toHaveBeenCalledOnce());
    act(() => sidecar.processEventHandlers.error[0]("permission denied"));

    expect(await screen.findByRole("heading", { name: "Failed to start local API" })).toBeInTheDocument();
    expect(screen.getByText("Error: Sidecar process error: permission denied")).toBeInTheDocument();
  });

  it("surfaces a timeout error with the xattr workaround when the sidecar never prints a port", async () => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", { value: {}, configurable: true });
    const sidecar = makeSidecar();
    bridge.sidecar.mockReturnValue(sidecar.command);

    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      render(
        <TauriProvider>
          <ContextProbe />
        </TauriProvider>,
      );

      await waitFor(() => expect(sidecar.command.spawn).toHaveBeenCalledOnce());
      // Sidecar spawned but never emits a port line (e.g. macOS blocks the
      // quarantined binary). The startup timeout should fire and surface the
      // xattr -cr guidance instead of hanging on "Starting local environment...".
      await act(async () => { await vi.advanceTimersByTimeAsync(30_000); });
      expect(await screen.findByRole("heading", { name: "Failed to start local API" })).toBeInTheDocument();
      expect(screen.getByText(/did not start in time/)).toBeInTheDocument();
      expect(screen.getByText(/xattr -cr/)).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });

  it("starts only one sidecar across React development effect replay", async () => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", { value: {}, configurable: true });
    const sidecar = makeSidecar();
    bridge.sidecar.mockReturnValue(sidecar.command);

    render(
      <React.StrictMode>
        <TauriProvider>
          <ContextProbe />
        </TauriProvider>
      </React.StrictMode>,
    );

    await waitFor(() => expect(sidecar.command.spawn).toHaveBeenCalledOnce());
    expect(bridge.sidecar).toHaveBeenCalledOnce();
  });
});
