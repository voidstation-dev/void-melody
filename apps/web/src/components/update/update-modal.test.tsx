// @vitest-environment jsdom

import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const bridge = vi.hoisted(() => ({
  appDataDir: vi.fn(),
  resolveResource: vi.fn(),
  sidecar: vi.fn(),
  check: vi.fn(),
  getVersion: vi.fn(),
  relaunch: vi.fn(),
}));

vi.mock("@tauri-apps/api/path", () => ({
  appDataDir: bridge.appDataDir,
  resolveResource: bridge.resolveResource,
}));
vi.mock("@tauri-apps/api/app", () => ({ getVersion: bridge.getVersion }));
vi.mock("@tauri-apps/plugin-shell", () => ({ Command: { sidecar: bridge.sidecar } }));
vi.mock("@tauri-apps/plugin-updater", () => ({ check: bridge.check }));
vi.mock("@tauri-apps/plugin-process", () => ({ relaunch: bridge.relaunch }));

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

function makeUpdate(overrides: Record<string, unknown> = {}) {
  return {
    rid: 1,
    available: true,
    currentVersion: "0.2.0",
    version: "0.3.0",
    date: "2026-08-02T00:00:00Z",
    body: "Faster local previews.",
    rawJson: {},
    download: vi.fn().mockResolvedValue(undefined),
    install: vi.fn().mockResolvedValue(undefined),
    downloadAndInstall: vi.fn().mockResolvedValue(undefined),
    close: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

async function renderModal(update: ReturnType<typeof makeUpdate>) {
  const [{ TauriProvider }, { UpdateProvider }, { I18nProvider }, { UpdateModal }] = await Promise.all([
    import("@/contexts/tauri-provider"),
    import("@/contexts/update-provider"),
    import("@/contexts/i18n-provider"),
    import("./update-modal"),
  ]);
  Object.defineProperty(window, "__TAURI_INTERNALS__", { configurable: true, value: {} });
  const stdoutHandlers: Array<(line: string) => void> = [];
  const child = { kill: vi.fn().mockResolvedValue(undefined) };
  const command = {
    stdout: { on: vi.fn((_event: string, handler: (line: string) => void) => stdoutHandlers.push(handler)) },
    stderr: { on: vi.fn() },
    spawn: vi.fn().mockResolvedValue(child),
  };
  bridge.sidecar.mockReturnValue(command);
  bridge.check.mockResolvedValue(update);

  render(
    <I18nProvider initialLocale="en">
      <TauriProvider>
        <UpdateProvider>
          <button>Workspace action</button>
          <UpdateModal />
        </UpdateProvider>
      </TauriProvider>
    </I18nProvider>,
  );
  await waitFor(() => expect(command.spawn).toHaveBeenCalledOnce());
  act(() => stdoutHandlers[0]("Listening on 127.0.0.1:45001"));
  await screen.findByRole("dialog");
  return { child, command, stdoutHandlers };
}

describe("UpdateModal", () => {
  beforeEach(() => {
    vi.resetModules();
    bridge.appDataDir.mockResolvedValue("/app-data");
    bridge.resolveResource.mockImplementation(async (path: string) => `/resources/${path}`);
    bridge.sidecar.mockReset();
    bridge.check.mockReset();
    bridge.getVersion.mockReset().mockResolvedValue("0.2.0");
    bridge.relaunch.mockReset().mockResolvedValue(undefined);
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "random-token") });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));
  });

  it("opens an accessible, focused dialog with plain-text update details", async () => {
    const notes = "Keep <img src=x onerror=alert(1)> as plain text.";
    const update = makeUpdate({ body: notes });
    await renderModal(update);

    const dialog = screen.getByRole("dialog", { name: "Update available" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByText("v0.2.0 → v0.3.0")).toBeInTheDocument();
    expect(screen.getByText("Released Aug 2, 2026")).toBeInTheDocument();
    expect(screen.getByText(notes)).toBeInTheDocument();
    expect(dialog.querySelector("img")).toBeNull();
    expect(screen.getByRole("button", { name: "Update now" })).toHaveFocus();

    fireEvent.keyDown(dialog, { key: "Escape" });
    await waitFor(() => expect(update.close).toHaveBeenCalledOnce());
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("lets the user choose Later without starting the download", async () => {
    const update = makeUpdate();
    await renderModal(update);

    await userEvent.click(screen.getByRole("button", { name: "Later" }));

    await waitFor(() => expect(update.close).toHaveBeenCalledOnce());
    expect(update.download).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("starts the update and presents determinate segmented download progress", async () => {
    let listener: ((event: unknown) => void) | undefined;
    const pending = deferred<void>();
    const update = makeUpdate({
      download: vi.fn((onEvent) => {
        listener = onEvent;
        return pending.promise;
      }),
    });
    await renderModal(update);

    await userEvent.click(screen.getByRole("button", { name: "Update now" }));
    act(() => {
      listener?.({ event: "Started", data: { contentLength: 200 } });
      listener?.({ event: "Progress", data: { chunkLength: 50 } });
    });

    const progress = await screen.findByRole("progressbar", { name: "Downloading update" });
    expect(progress).toHaveAttribute("aria-valuemin", "0");
    expect(progress).toHaveAttribute("aria-valuemax", "200");
    expect(progress).toHaveAttribute("aria-valuenow", "50");
    expect(screen.getByText("25%" )).toBeInTheDocument();
    expect(update.download).toHaveBeenCalledOnce();
  });

  it("presents indeterminate progress when the download total is unknown", async () => {
    let listener: ((event: unknown) => void) | undefined;
    const pending = deferred<void>();
    const update = makeUpdate({
      download: vi.fn((onEvent) => {
        listener = onEvent;
        return pending.promise;
      }),
    });
    await renderModal(update);

    await userEvent.click(screen.getByRole("button", { name: "Update now" }));
    act(() => {
      listener?.({ event: "Started", data: {} });
      listener?.({ event: "Progress", data: { chunkLength: 50 } });
    });

    const progress = await screen.findByRole("progressbar", { name: "Downloading update" });
    expect(progress).not.toHaveAttribute("aria-valuenow");
    expect(screen.getByText("Downloading update…")).toBeInTheDocument();
  });

  it("offers a retry after failure and rechecks for a fresh update resource", async () => {
    const update = makeUpdate({
      download: vi.fn().mockRejectedValue(new Error("network interrupted")),
    });
    const retryUpdate = makeUpdate();
    await renderModal(update);
    bridge.check.mockResolvedValueOnce(retryUpdate);

    await userEvent.click(screen.getByRole("button", { name: "Update now" }));

    expect(await screen.findByRole("dialog", { name: "Update could not finish" })).toBeInTheDocument();
    expect(screen.getByText("Could not download the update. Try again.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("dialog", { name: "Update available" })).toBeInTheDocument();
    expect(bridge.check).toHaveBeenCalledTimes(2);
  });
});
