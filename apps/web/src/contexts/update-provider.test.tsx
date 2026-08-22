// @vitest-environment jsdom

import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const bridge = vi.hoisted(() => ({
  appDataDir: vi.fn(),
  resolveResource: vi.fn(),
  setApiConnection: vi.fn(),
  sidecar: vi.fn(),
  invoke: vi.fn(),
  check: vi.fn(),
  getVersion: vi.fn(),
  relaunch: vi.fn(),
  updaterModuleLoads: 0,
}));

vi.mock("@tauri-apps/api/path", () => ({
  appDataDir: bridge.appDataDir,
  resolveResource: bridge.resolveResource,
}));

vi.mock("@tauri-apps/api/app", () => ({ getVersion: bridge.getVersion }));

vi.mock("@tauri-apps/api/core", () => ({
  invoke: bridge.invoke,
}));

vi.mock("@tauri-apps/plugin-shell", () => ({
  Command: { sidecar: bridge.sidecar },
}));

vi.mock("@/lib/api-client", () => ({ setApiConnection: bridge.setApiConnection }));

vi.mock("@tauri-apps/plugin-updater", () => {
  bridge.updaterModuleLoads += 1;
  return { check: bridge.check };
});

vi.mock("@tauri-apps/plugin-process", () => ({ relaunch: bridge.relaunch }));

type OutputHandler = (line: string) => void;

function makeSidecar() {
  const stdoutHandlers: OutputHandler[] = [];
  const child = { pid: 41_004, kill: vi.fn().mockResolvedValue(undefined) };
  const command = {
    stdout: { on: vi.fn((_event: string, handler: OutputHandler) => stdoutHandlers.push(handler)) },
    stderr: { on: vi.fn() },
    on: vi.fn(),
    spawn: vi.fn().mockResolvedValue(child),
  };
  return { child, command, stdoutHandlers };
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

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, reject, resolve };
}

async function renderHarness({ desktop = true }: { desktop?: boolean } = {}) {
  const [{ TauriProvider }, { UpdateProvider, useUpdate }] = await Promise.all([
    import("./tauri-provider"),
    import("./update-provider"),
  ]);

  function UpdateProbe() {
    const update = useUpdate();
    return (
      <div>
        <output data-testid="status">{update.status}</output>
        <output data-testid="version">{update.currentVersion}</output>
        <output data-testid="available">
          {update.availableUpdate
            ? `${update.availableUpdate.currentVersion}|${update.availableUpdate.version}|${update.availableUpdate.date}|${update.availableUpdate.notes}`
            : "none"}
        </output>
        <output data-testid="error">{update.errorMessage ?? "none"}</output>
        <output data-testid="progress">
          {update.downloadedBytes}/{update.totalBytes ?? "unknown"}
        </output>
        <button onClick={() => void update.checkForUpdates({ interactive: true })}>Check</button>
        <button onClick={() => void update.installAvailableUpdate()}>Install</button>
        <button onClick={() => void update.dismissUpdate()}>Later</button>
      </div>
    );
  }

  Object.defineProperty(window, "__TAURI_INTERNALS__", {
    configurable: true,
    value: desktop ? {} : undefined,
  });
  const sidecar = makeSidecar();
  bridge.sidecar.mockReturnValue(sidecar.command);

  render(
    <TauriProvider>
      <UpdateProvider>
        <UpdateProbe />
      </UpdateProvider>
    </TauriProvider>,
  );

  if (desktop) {
    await waitFor(() => expect(sidecar.command.spawn).toHaveBeenCalledOnce());
    act(() => sidecar.stdoutHandlers[0]("Listening on 127.0.0.1:43001"));
  }

  await screen.findByTestId("status");
  return sidecar;
}

describe("UpdateProvider checks", () => {
  beforeEach(() => {
    vi.resetModules();
    bridge.appDataDir.mockResolvedValue("/app-data");
    bridge.resolveResource.mockImplementation(async (path: string) => `/resources/${path}`);
    bridge.setApiConnection.mockReset();
    bridge.sidecar.mockReset();
    bridge.invoke.mockReset().mockImplementation(async (command: string) => {
      if (command === "get_sidecar_process_identity") return "1700000000000000";
      return {
        platform: "macos",
        arch: "aarch64",
        targetTriple: "aarch64-apple-darwin",
        hostEnvironmentRequired: [],
        resources: [
          { name: "bin/Voice.json", present: true },
          { name: "bin/ffmpeg", present: true },
          { name: "bin/melody-api-aarch64-apple-darwin", present: true },
        ],
      };
    });
    bridge.check.mockReset();
    bridge.getVersion.mockReset().mockResolvedValue("0.2.0");
    bridge.relaunch.mockReset().mockResolvedValue(undefined);
    bridge.updaterModuleLoads = 0;
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "random-token") });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reports the runtime version and up-to-date state when no update exists", async () => {
    bridge.check.mockResolvedValue(null);

    await renderHarness();

    expect(await screen.findByText("up-to-date")).toBeInTheDocument();
    expect(screen.getByTestId("version")).toHaveTextContent("0.2.0");
    expect(screen.getByTestId("available")).toHaveTextContent("none");
  });

  it("exposes validated update metadata returned by the desktop updater", async () => {
    const update = makeUpdate();
    bridge.check.mockResolvedValue(update);

    await renderHarness();

    expect(await screen.findByText("available")).toBeInTheDocument();
    expect(screen.getByTestId("available")).toHaveTextContent(
      "0.2.0|0.3.0|2026-08-02T00:00:00Z|Faster local previews.",
    );
  });

  it("rejects malformed metadata, closes its resource, and never renders it", async () => {
    const malformed = makeUpdate({ version: "" });
    bridge.check.mockResolvedValueOnce(null).mockResolvedValueOnce(malformed);
    await renderHarness();
    await screen.findByText("up-to-date");

    fireEvent.click(screen.getByRole("button", { name: "Check" }));

    expect(await screen.findByText("error")).toBeInTheDocument();
    expect(screen.getByTestId("error")).toHaveTextContent("Update information could not be read. Try again.");
    expect(screen.getByTestId("available")).toHaveTextContent("none");
    expect(malformed.close).toHaveBeenCalledOnce();
  });

  it("rejects an invalid release date instead of passing it to the update UI", async () => {
    const malformed = makeUpdate({ date: "not-a-date" });
    bridge.check.mockResolvedValueOnce(null).mockResolvedValueOnce(malformed);
    await renderHarness();
    await screen.findByText("up-to-date");

    fireEvent.click(screen.getByRole("button", { name: "Check" }));

    expect(await screen.findByText("error")).toBeInTheDocument();
    expect(screen.getByTestId("available")).toHaveTextContent("none");
    expect(malformed.close).toHaveBeenCalledOnce();
  });

  it("keeps startup check failures silent but shows a manual failure", async () => {
    bridge.check
      .mockRejectedValueOnce(new Error("offline at launch"))
      .mockRejectedValueOnce(new Error("offline on demand"));
    await renderHarness();

    await waitFor(() => expect(bridge.check).toHaveBeenCalledOnce());
    expect(screen.getByTestId("status")).toHaveTextContent("idle");
    expect(screen.getByTestId("error")).toHaveTextContent("none");

    fireEvent.click(screen.getByRole("button", { name: "Check" }));

    expect(await screen.findByText("error")).toBeInTheDocument();
    expect(screen.getByTestId("error")).toHaveTextContent("Could not check for updates. Try again.");
  });

  it("closes an available update and suppresses its prompt for this session when dismissed", async () => {
    const update = makeUpdate();
    bridge.check.mockResolvedValue(update);
    await renderHarness();
    await screen.findByText("available");

    fireEvent.click(screen.getByRole("button", { name: "Later" }));

    await waitFor(() => expect(update.close).toHaveBeenCalledOnce());
    expect(screen.getByTestId("status")).toHaveTextContent("idle");
    expect(screen.getByTestId("available")).toHaveTextContent("none");
    expect(bridge.check).toHaveBeenCalledOnce();
  });

  it("shares one in-flight updater check across repeated requests", async () => {
    const pending = deferred<null>();
    bridge.check.mockReturnValue(pending.promise);
    await renderHarness();
    await waitFor(() => expect(bridge.check).toHaveBeenCalledOnce());

    fireEvent.click(screen.getByRole("button", { name: "Check" }));
    fireEvent.click(screen.getByRole("button", { name: "Check" }));
    expect(bridge.check).toHaveBeenCalledOnce();

    pending.resolve(null);
    expect(await screen.findByText("up-to-date")).toBeInTheDocument();
  });

  it("is a browser no-op and never loads or calls the desktop updater", async () => {
    bridge.check.mockResolvedValue(makeUpdate());

    await renderHarness({ desktop: false });
    fireEvent.click(screen.getByRole("button", { name: "Check" }));

    await waitFor(() => expect(screen.getByTestId("version")).toHaveTextContent("dev"));
    expect(screen.getByTestId("status")).toHaveTextContent("idle");
    expect(bridge.check).not.toHaveBeenCalled();
    expect(bridge.updaterModuleLoads).toBe(0);
  });

  it("checks exactly once after readiness even if the update subtree remounts", async () => {
    bridge.check.mockResolvedValue(null);
    const [{ TauriProvider }, { UpdateProvider, useUpdate }] = await Promise.all([
      import("./tauri-provider"),
      import("./update-provider"),
    ]);
    Object.defineProperty(window, "__TAURI_INTERNALS__", { configurable: true, value: {} });
    const sidecar = makeSidecar();
    bridge.sidecar.mockReturnValue(sidecar.command);

    function Status() {
      return <output data-testid="update-mounted">{useUpdate().status}</output>;
    }

    function LifecycleToggle() {
      const [visible, setVisible] = React.useState(true);
      return (
        <div>
          <button onClick={() => setVisible((value) => !value)}>Toggle updates</button>
          {visible && (
            <UpdateProvider>
              <Status />
            </UpdateProvider>
          )}
        </div>
      );
    }

    render(
      <TauriProvider>
        <LifecycleToggle />
      </TauriProvider>,
    );
    await waitFor(() => expect(sidecar.command.spawn).toHaveBeenCalledOnce());
    act(() => sidecar.stdoutHandlers[0]("Listening on 127.0.0.1:43003"));
    await screen.findByText("up-to-date");

    fireEvent.click(screen.getByRole("button", { name: "Toggle updates" }));
    await waitFor(() => expect(screen.queryByTestId("update-mounted")).not.toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Toggle updates" }));
    await screen.findByTestId("update-mounted");
    await waitFor(() => expect(bridge.check).toHaveBeenCalledOnce());
  });

  it("delivers a deferred startup update to the active StrictMode remount without checking twice", async () => {
    const pending = deferred<ReturnType<typeof makeUpdate> | null>();
    const update = makeUpdate();
    bridge.check.mockReturnValue(pending.promise);
    const [{ TauriProvider }, { UpdateProvider, useUpdate }] = await Promise.all([
      import("./tauri-provider"),
      import("./update-provider"),
    ]);
    Object.defineProperty(window, "__TAURI_INTERNALS__", { configurable: true, value: {} });
    const sidecar = makeSidecar();
    bridge.sidecar.mockReturnValue(sidecar.command);

    function Status() {
      const { status, availableUpdate } = useUpdate();
      return <output data-testid="replacement-update">{`${status}:${availableUpdate?.version ?? "none"}`}</output>;
    }

    function LifecycleToggle() {
      const [visible, setVisible] = React.useState(true);
      return (
        <div>
          <button onClick={() => setVisible((value) => !value)}>Toggle updates</button>
          {visible && (
            <UpdateProvider>
              <Status />
            </UpdateProvider>
          )}
        </div>
      );
    }

    render(
      <React.StrictMode>
        <TauriProvider>
          <LifecycleToggle />
        </TauriProvider>
      </React.StrictMode>,
    );
    await waitFor(() => expect(sidecar.command.spawn).toHaveBeenCalledOnce());
    act(() => sidecar.stdoutHandlers[0]("Listening on 127.0.0.1:43004"));
    await waitFor(() => expect(bridge.check).toHaveBeenCalledOnce());

    fireEvent.click(screen.getByRole("button", { name: "Toggle updates" }));
    await waitFor(() => expect(screen.queryByTestId("replacement-update")).not.toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Toggle updates" }));
    await screen.findByTestId("replacement-update");

    act(() => pending.resolve(update));

    expect(await screen.findByTestId("replacement-update")).toHaveTextContent("available:0.3.0");
    expect(bridge.check).toHaveBeenCalledOnce();
    expect(update.close).not.toHaveBeenCalled();
  });

  it("closes an update that resolves after its provider permanently unmounts", async () => {
    const pending = deferred<ReturnType<typeof makeUpdate> | null>();
    const update = makeUpdate();
    bridge.check.mockReturnValue(pending.promise);
    const [{ TauriProvider }, { UpdateProvider, useUpdate }] = await Promise.all([
      import("./tauri-provider"),
      import("./update-provider"),
    ]);
    Object.defineProperty(window, "__TAURI_INTERNALS__", { configurable: true, value: {} });
    const sidecar = makeSidecar();
    bridge.sidecar.mockReturnValue(sidecar.command);

    function Status() {
      return <output>{useUpdate().status}</output>;
    }

    const view = render(
      <TauriProvider>
        <UpdateProvider>
          <Status />
        </UpdateProvider>
      </TauriProvider>,
    );
    await waitFor(() => expect(sidecar.command.spawn).toHaveBeenCalledOnce());
    act(() => sidecar.stdoutHandlers[0]("Listening on 127.0.0.1:43005"));
    await waitFor(() => expect(bridge.check).toHaveBeenCalledOnce());

    view.unmount();
    act(() => pending.resolve(update));

    await waitFor(() => expect(update.close).toHaveBeenCalledOnce());
  });

  it("resolves dismissUpdate only after its update resource closes", async () => {
    const closePending = deferred<void>();
    const update = makeUpdate({ close: vi.fn(() => closePending.promise) });
    bridge.check.mockResolvedValue(update);
    const [{ TauriProvider }, { UpdateProvider, useUpdate }] = await Promise.all([
      import("./tauri-provider"),
      import("./update-provider"),
    ]);
    Object.defineProperty(window, "__TAURI_INTERNALS__", { configurable: true, value: {} });
    const sidecar = makeSidecar();
    bridge.sidecar.mockReturnValue(sidecar.command);
    let dismissUpdate: (() => unknown) | undefined;

    function DismissProbe() {
      const updateContext = useUpdate();
      dismissUpdate = updateContext.dismissUpdate;
      return <output data-testid="dismiss-status">{updateContext.status}</output>;
    }

    render(
      <TauriProvider>
        <UpdateProvider>
          <DismissProbe />
        </UpdateProvider>
      </TauriProvider>,
    );
    await waitFor(() => expect(sidecar.command.spawn).toHaveBeenCalledOnce());
    act(() => sidecar.stdoutHandlers[0]("Listening on 127.0.0.1:43006"));
    await screen.findByText("available");

    const completion = dismissUpdate?.();
    expect(completion).toBeInstanceOf(Promise);
    let resolved = false;
    const completed = Promise.resolve(completion).then(() => {
      resolved = true;
    });
    await Promise.resolve();
    expect(update.close).toHaveBeenCalledOnce();
    expect(resolved).toBe(false);

    closePending.resolve(undefined);
    await completed;
    expect(resolved).toBe(true);
  });
});

describe("UpdateProvider installation", () => {
  beforeEach(() => {
    vi.resetModules();
    bridge.appDataDir.mockResolvedValue("/app-data");
    bridge.resolveResource.mockImplementation(async (path: string) => `/resources/${path}`);
    bridge.setApiConnection.mockReset();
    bridge.sidecar.mockReset();
    bridge.invoke.mockReset().mockResolvedValue({
      platform: "macos",
      arch: "aarch64",
      targetTriple: "aarch64-apple-darwin",
      hostEnvironmentRequired: [],
      resources: [
        { name: "bin/Voice.json", present: true },
        { name: "bin/ffmpeg", present: true },
        { name: "bin/melody-api-aarch64-apple-darwin", present: true },
      ],
    });
    bridge.check.mockReset();
    bridge.getVersion.mockReset().mockResolvedValue("0.2.0");
    bridge.relaunch.mockReset().mockResolvedValue(undefined);
    bridge.updaterModuleLoads = 0;
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "random-token") });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("tracks cumulative download bytes against a known total", async () => {
    let onEvent: ((event: unknown) => void) | undefined;
    const pending = deferred<void>();
    const update = makeUpdate({
      download: vi.fn((listener) => {
        onEvent = listener;
        return pending.promise;
      }),
    });
    bridge.check.mockResolvedValue(update);
    await renderHarness();
    await screen.findByText("available");

    fireEvent.click(screen.getByRole("button", { name: "Install" }));
    expect(await screen.findByText("downloading")).toBeInTheDocument();
    act(() => {
      onEvent?.({ event: "Started", data: { contentLength: 100 } });
      onEvent?.({ event: "Progress", data: { chunkLength: 25 } });
      onEvent?.({ event: "Progress", data: { chunkLength: 15 } });
    });

    expect(screen.getByTestId("progress")).toHaveTextContent("40/100");
  });

  it("keeps progress indeterminate when the server omits a download total", async () => {
    let onEvent: ((event: unknown) => void) | undefined;
    const pending = deferred<void>();
    const update = makeUpdate({
      download: vi.fn((listener) => {
        onEvent = listener;
        return pending.promise;
      }),
    });
    bridge.check.mockResolvedValue(update);
    await renderHarness();
    await screen.findByText("available");

    fireEvent.click(screen.getByRole("button", { name: "Install" }));
    await screen.findByText("downloading");
    act(() => {
      onEvent?.({ event: "Started", data: {} });
      onEvent?.({ event: "Progress", data: { chunkLength: 20 } });
    });

    expect(screen.getByTestId("progress")).toHaveTextContent("20/unknown");
  });

  it("reports a download failure without shutting down the sidecar", async () => {
    const update = makeUpdate({
      download: vi.fn().mockRejectedValue(new Error("download unavailable")),
    });
    bridge.check.mockResolvedValue(update);
    const sidecar = await renderHarness();
    await screen.findByText("available");

    fireEvent.click(screen.getByRole("button", { name: "Install" }));

    expect(await screen.findByText("error")).toBeInTheDocument();
    expect(screen.getByTestId("error")).toHaveTextContent("Could not download the update. Try again.");
    expect(sidecar.child.kill).not.toHaveBeenCalled();
  });

  it("downloads, shuts down, installs, closes, and relaunches in order", async () => {
    const order: string[] = [];
    const update = makeUpdate({
      download: vi.fn(async () => {
        order.push("download");
      }),
      install: vi.fn(async () => {
        order.push("install");
      }),
      close: vi.fn(async () => {
        order.push("close");
      }),
    });
    bridge.check.mockResolvedValue(update);
    bridge.relaunch.mockImplementation(async () => {
      order.push("relaunch");
    });
    const sidecar = await renderHarness();
    bridge.invoke.mockImplementation(async (command: string) => {
      if (command === "terminate_sidecar_pid") {
        order.push("shutdown");
        return;
      }
      if (command === "get_sidecar_process_identity") return "1700000000000000";
      return {
        platform: "macos",
        arch: "aarch64",
        targetTriple: "aarch64-apple-darwin",
        hostEnvironmentRequired: [],
        resources: [
          { name: "bin/Voice.json", present: true },
          { name: "bin/ffmpeg", present: true },
          { name: "bin/melody-api-aarch64-apple-darwin", present: true },
        ],
      };
    });
    await screen.findByText("available");

    fireEvent.click(screen.getByRole("button", { name: "Install" }));

    await waitFor(() => expect(bridge.relaunch).toHaveBeenCalledOnce());
    expect(order).toEqual(["download", "shutdown", "install", "close", "relaunch"]);
  });

  it("restarts the sidecar and exposes a retryable error when install fails", async () => {
    const update = makeUpdate({ install: vi.fn().mockRejectedValue(new Error("install denied")) });
    bridge.check.mockResolvedValue(update);
    const sidecar = await renderHarness();
    await screen.findByText("available");

    fireEvent.click(screen.getByRole("button", { name: "Install" }));
    await waitFor(() => expect(sidecar.command.spawn).toHaveBeenCalledTimes(2));
    act(() => sidecar.stdoutHandlers[1]("Listening on 127.0.0.1:43002"));

    expect(await screen.findByText("error")).toBeInTheDocument();
    expect(screen.getByTestId("error")).toHaveTextContent("Could not install the update. Try again.");
    expect(update.close).toHaveBeenCalledOnce();
    expect(bridge.relaunch).not.toHaveBeenCalled();
  });

  it("shares one in-flight install across repeated requests", async () => {
    const pending = deferred<void>();
    const update = makeUpdate({ download: vi.fn(() => pending.promise) });
    bridge.check.mockResolvedValue(update);
    await renderHarness();
    await screen.findByText("available");

    fireEvent.click(screen.getByRole("button", { name: "Install" }));
    fireEvent.click(screen.getByRole("button", { name: "Install" }));

    expect(update.download).toHaveBeenCalledOnce();
  });
});
