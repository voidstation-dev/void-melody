// @vitest-environment jsdom

import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const bridge = vi.hoisted(() => ({
  appDataDir: vi.fn(),
  resolveResource: vi.fn(),
  sidecar: vi.fn(),
  check: vi.fn(),
  getVersion: vi.fn(),
  updaterModuleLoads: 0,
}));

vi.mock("@tauri-apps/api/path", () => ({
  appDataDir: bridge.appDataDir,
  resolveResource: bridge.resolveResource,
}));
vi.mock("@tauri-apps/api/app", () => ({ getVersion: bridge.getVersion }));
vi.mock("@tauri-apps/plugin-shell", () => ({ Command: { sidecar: bridge.sidecar } }));
vi.mock("@tauri-apps/plugin-updater", () => {
  bridge.updaterModuleLoads += 1;
  return { check: bridge.check };
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

async function renderSettings(desktop: boolean) {
  const [{ TauriProvider }, { UpdateProvider }, { I18nProvider }, { UpdateSettings }] = await Promise.all([
    import("@/contexts/tauri-provider"),
    import("@/contexts/update-provider"),
    import("@/contexts/i18n-provider"),
    import("./update-settings"),
  ]);
  Object.defineProperty(window, "__TAURI_INTERNALS__", {
    configurable: true,
    value: desktop ? {} : undefined,
  });
  const stdoutHandlers: Array<(line: string) => void> = [];
  const command = {
    stdout: { on: vi.fn((_event: string, handler: (line: string) => void) => stdoutHandlers.push(handler)) },
    stderr: { on: vi.fn() },
    spawn: vi.fn().mockResolvedValue({ kill: vi.fn().mockResolvedValue(undefined) }),
  };
  bridge.sidecar.mockReturnValue(command);

  render(
    <I18nProvider initialLocale="en">
      <TauriProvider>
        <UpdateProvider>
          <UpdateSettings />
        </UpdateProvider>
      </TauriProvider>
    </I18nProvider>,
  );

  if (desktop) {
    await waitFor(() => expect(command.spawn).toHaveBeenCalledOnce());
    act(() => stdoutHandlers[0]("Listening on 127.0.0.1:44001"));
  }
}

describe("UpdateSettings", () => {
  beforeEach(() => {
    vi.resetModules();
    bridge.appDataDir.mockResolvedValue("/app-data");
    bridge.resolveResource.mockImplementation(async (path: string) => `/resources/${path}`);
    bridge.sidecar.mockReset();
    bridge.check.mockReset();
    bridge.getVersion.mockReset().mockResolvedValue("0.2.0");
    bridge.updaterModuleLoads = 0;
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "random-token") });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));
  });

  it("labels updates as desktop-only in browser mode without loading the updater", async () => {
    await renderSettings(false);

    expect(await screen.findByText("Current version")).toBeInTheDocument();
    expect(screen.getByLabelText("Current version")).toHaveTextContent("vdev");
    expect(screen.getByText("Updates are available in the desktop app.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Desktop app only" })).toBeDisabled();
    expect(bridge.check).not.toHaveBeenCalled();
    expect(bridge.updaterModuleLoads).toBe(0);
  });

  it("shows the runtime version and a single-flight manual update action on desktop", async () => {
    const manualCheck = deferred<null>();
    bridge.check.mockResolvedValueOnce(null).mockReturnValueOnce(manualCheck.promise);
    await renderSettings(true);
    // currentVersion starts at "dev" and is updated asynchronously once
    // getRuntimeVersion() resolves, so wait for the settled text rather than
    // asserting synchronously on the first render.
    await waitFor(() =>
      expect(screen.getByLabelText("Current version")).toHaveTextContent("v0.2.0"),
    );
    expect(bridge.getVersion).toHaveBeenCalled();
    await waitFor(() => expect(bridge.check).toHaveBeenCalledOnce());

    fireEvent.click(screen.getByRole("button", { name: "Check for updates" }));

    expect(await screen.findByRole("button", { name: "Checking for updates" })).toBeDisabled();
    expect(bridge.check).toHaveBeenCalledTimes(2);
    manualCheck.resolve(null);
    expect(await screen.findByText("You’re up to date.")).toBeInTheDocument();
  });
});
