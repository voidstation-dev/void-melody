"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Command, type Child } from "@tauri-apps/plugin-shell";
import { invoke } from "@tauri-apps/api/core";
import { appDataDir, resolveResource } from "@tauri-apps/api/path";
import { Loader2 } from "lucide-react";
import { setApiConnection } from "@/lib/api-client";
import {
  buildSidecarEnvironment,
  evaluateNativePreflight,
  formatPreflightFailure,
  type RuntimePreflight,
  type RuntimePreflightFailure,
  validateSidecarEnvironment,
} from "@/lib/desktop-runtime-preflight";

type TauriContextValue = {
  isDesktop: boolean;
  isReady: boolean;
  shutdownSidecar: () => Promise<void>;
  restartSidecar: () => Promise<void>;
};

const TauriContext = createContext<TauriContextValue | null>(null);
const STARTUP_TIMEOUT_MESSAGE = "Local API did not start in time";
const SIDECAR_PROCESS_ERROR_MESSAGE = "Sidecar process error";
const GENERIC_STARTUP_ERROR_MESSAGE = "Sidecar failed to start";
const SIDECAR_EXIT_MESSAGE = /^Sidecar exited before API became ready \((exit code|signal) (-?\d+)\)$/;

function formatStartupError(reason: unknown) {
  if (!(reason instanceof Error)) return GENERIC_STARTUP_ERROR_MESSAGE;

  if (
    reason.message === STARTUP_TIMEOUT_MESSAGE ||
    reason.message === SIDECAR_PROCESS_ERROR_MESSAGE
  ) {
    return reason.message;
  }

  const exitMatch = reason.message.match(SIDECAR_EXIT_MESSAGE);
  if (exitMatch && Number.isSafeInteger(Number(exitMatch[2]))) {
    return `Sidecar exited before API became ready (${exitMatch[1]} ${Number(exitMatch[2])})`;
  }

  return GENERIC_STARTUP_ERROR_MESSAGE;
}

function hasTauriRuntime() {
  return (
    typeof window !== "undefined" &&
    Boolean(
      (window as Window & { __TAURI_INTERNALS__?: unknown })
        .__TAURI_INTERNALS__,
    )
  );
}

function runtimePlatformLabel(failure: RuntimePreflightFailure) {
  if (failure.platform === "macos" && failure.targetTriple.startsWith("aarch64-")) {
    return "macOS ARM64";
  }

  if (failure.platform === "windows" && failure.targetTriple.startsWith("x86_64-")) {
    return "Windows x64";
  }

  return null;
}

export function useTauri() {
  const context = useContext(TauriContext);
  if (!context) {
    throw new Error("useTauri must be used within TauriProvider");
  }
  return context;
}

export function TauriProvider({ children }: { children: React.ReactNode }) {
  const [isDesktop, setIsDesktop] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preflightFailure, setPreflightFailure] =
    useState<RuntimePreflightFailure | null>(null);
  const mountedRef = useRef(false);
  const sidecarProcessRef = useRef<Child | null>(null);
  const startPromiseRef = useRef<Promise<void> | null>(null);
  const shutdownPromiseRef = useRef<Promise<void> | null>(null);
  const restartPromiseRef = useRef<Promise<void> | null>(null);

  const startSidecar = useCallback(() => {
    if (startPromiseRef.current) return startPromiseRef.current;

    const start = (async () => {
      const runtimePreflight = await invoke<RuntimePreflight>(
        "get_runtime_preflight",
      );
      const nativePreflight = evaluateNativePreflight(runtimePreflight);
      if (!nativePreflight.ok) {
        setPreflightFailure({
          platform: runtimePreflight.platform,
          targetTriple: runtimePreflight.targetTriple,
          missingEnv: [],
          missingResources: nativePreflight.missingResources,
        });
        return;
      }

      const apiToken = crypto.randomUUID();
      const [dataDir, catalogPath] = await Promise.all([
        appDataDir(),
        resolveResource("bin/Voice.json"),
      ]);
      const env = buildSidecarEnvironment({ apiToken, dataDir, catalogPath });
      const environmentPreflight = validateSidecarEnvironment(env);
      if (!environmentPreflight.ok) {
        setPreflightFailure({
          platform: runtimePreflight.platform,
          targetTriple: runtimePreflight.targetTriple,
          missingEnv: environmentPreflight.missing,
          missingResources: [],
        });
        return;
      }

      console.info("Starting sidecar runtime", {
        platform: runtimePreflight.platform,
        targetTriple: runtimePreflight.targetTriple,
        environmentKeys: Object.keys(env),
      });

      const sidecar = Command.sidecar("bin/melody-api", [], {
        env,
      });

      let resolveReady: (() => void) | undefined;
      let rejectReady: ((reason: Error) => void) | undefined;
      let didResolve = false;
      let didReject = false;
      const readyPromise = new Promise<void>((resolve, reject) => {
        resolveReady = resolve;
        rejectReady = reject;
      });

      // If the sidecar never prints a port (e.g. macOS Gatekeeper quarantines
      // the bundled binary and blocks its launch silently), the ready promise
      // would never settle and the UI would hang on "Starting local
      // environment..." forever. Time out so the user gets actionable guidance.
      const startupTimeoutMs = 30_000;
      let startupTimer: ReturnType<typeof setTimeout>;
      const rejectStartup = (reason: Error) => {
        if (didResolve || didReject || !mountedRef.current) return;
        didReject = true;
        clearTimeout(startupTimer);
        rejectReady?.(reason);
      };
      startupTimer = setTimeout(
        () => rejectStartup(new Error(STARTUP_TIMEOUT_MESSAGE)),
        startupTimeoutMs,
      );

      const portDetectionBuffers: Record<"STDOUT" | "STDERR", string> = {
        STDOUT: "",
        STDERR: "",
      };

      const probeHealth = async (url: string) => {
        for (let attempt = 0; attempt < 15; attempt++) {
          try {
            const response = await fetch(`${url}/api/v1/health/live`, {
              method: "GET",
            });
            if (response.ok && mountedRef.current && !didResolve && !didReject) {
              didResolve = true;
              clearTimeout(startupTimer);
              console.log(`Successfully connected to API at ${url}`);
              setApiConnection(url, apiToken);
              setIsReady(true);
              resolveReady?.();
              return true;
            }
          } catch {
            // The sidecar may log its address before it is ready to accept requests.
          }
          if (didResolve || didReject || !mountedRef.current) break;
          await new Promise((r) => setTimeout(r, 500));
        }
        return false;
      };

      const handleOutput = (line: string, source: "STDOUT" | "STDERR") => {
        if (didResolve || didReject || !mountedRef.current) return;
        const normalizedLine = `${portDetectionBuffers[source]}${line}`.replace(
          /\u001b\[[0-?]*[ -/]*[@-~]/g,
          "",
        );
        portDetectionBuffers[source] = normalizedLine.slice(-1024);
        // Ignore HTTP access log lines like `INFO: 127.0.0.1:55140 - "GET ..."`
        if (
          /-\s+"[A-Z]+\s+/.test(normalizedLine) ||
          /(?:INFO|DEBUG|WARNING|ERROR):\s+\d+\.\d+\.\d+\.\d+:\d+/.test(
            normalizedLine,
          )
        )
          return;
        const match =
          normalizedLine.match(
            /(?:running on|listening on|server started at port|port:?)\s*(?:https?:\/\/)?(?:127\.0\.0\.1|localhost|0\.0\.0\.0)?:?(\d{4,5})/i,
          ) ??
          normalizedLine.match(
            /(?:https?:\/\/)(?:127\.0\.0\.1|localhost|0\.0\.0\.0):(\d{4,5})/,
          );
        const port = match?.[1];
        if (port && port !== "0" && mountedRef.current && !didReject) {
          console.log(`Resolved local API port from ${source}: ${port}`);
          void probeHealth(`http://127.0.0.1:${port}`);
        }
      };

      sidecar.stdout.on("data", (line) => handleOutput(line, "STDOUT"));
      sidecar.stderr.on("data", (line) => handleOutput(line, "STDERR"));
      sidecar.on("error", () => {
        rejectStartup(new Error(SIDECAR_PROCESS_ERROR_MESSAGE));
      });
      sidecar.on("close", ({ code, signal }) => {
        const exitReason =
          code !== null && code !== undefined
            ? `exit code ${code}`
            : signal !== null && signal !== undefined
              ? `signal ${signal}`
              : "unknown reason";
        rejectStartup(
          new Error(`Sidecar exited before API became ready (${exitReason})`),
        );
      });

      const process = await sidecar.spawn();
      if (!mountedRef.current) {
        clearTimeout(startupTimer);
        try {
          await process.kill();
        } catch {
          // ignore
        }
        throw new Error("Sidecar provider unmounted during startup");
      }
      sidecarProcessRef.current = process;

      return readyPromise;
    })();
    startPromiseRef.current = start.finally(() => {
      startPromiseRef.current = null;
    });
    return startPromiseRef.current;
  }, []);

  const shutdownSidecar = useCallback(async () => {
    if (!hasTauriRuntime()) return;
    if (shutdownPromiseRef.current) return shutdownPromiseRef.current;

    const process = sidecarProcessRef.current;
    sidecarProcessRef.current = null;
    const shutdown = (async () => {
      if (process) {
        try {
          await process.kill();
        } catch {
          // ignore
        }
      }
    })();
    shutdownPromiseRef.current = shutdown.finally(() => {
      shutdownPromiseRef.current = null;
    });
    return shutdownPromiseRef.current;
  }, []);

  const restartSidecar = useCallback(async () => {
    if (!hasTauriRuntime()) return;
    if (restartPromiseRef.current) return restartPromiseRef.current;

    setError(null);
    const restart = (async () => {
      await shutdownSidecar();
      await startSidecar();
    })();
    restartPromiseRef.current = restart.finally(() => {
      restartPromiseRef.current = null;
    });
    return restartPromiseRef.current;
  }, [shutdownSidecar, startSidecar]);

  const handleRestart = useCallback(() => {
    void restartSidecar().catch((reason: unknown) => {
      console.error("Failed to restart Tauri sidecar");
      if (mountedRef.current) setError(formatStartupError(reason));
    });
  }, [restartSidecar]);

  useEffect(() => {
    mountedRef.current = true;
    const desktop = hasTauriRuntime();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsDesktop(desktop);

    if (!desktop) {
      setIsReady(true);
      return () => {
        mountedRef.current = false;
      };
    }

    void startSidecar().catch((reason: unknown) => {
      console.error("Failed to bootstrap Tauri sidecar");
      if (mountedRef.current) {
        setError(formatStartupError(reason));
      }
    });

    return () => {
      mountedRef.current = false;
      const process = sidecarProcessRef.current;
      sidecarProcessRef.current = null;
      if (process) void process.kill();
    };
  }, [startSidecar]);

  const contextValue = useMemo(
    () => ({ isDesktop, isReady, shutdownSidecar, restartSidecar }),
    [isDesktop, isReady, restartSidecar, shutdownSidecar],
  );

  if (error) {
    const isStartupTimeout = error === STARTUP_TIMEOUT_MESSAGE;
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 p-8 text-center text-destructive">
        <h2 className="text-xl font-bold">Failed to start local API</h2>
        <p className="font-mono text-sm">{error}</p>
        <button
          type="button"
          onClick={handleRestart}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
        >
          Restart API / Thử lại
        </button>
        {isStartupTimeout && (
          <div className="max-w-md text-sm text-muted-foreground text-left space-y-2 mt-2">
            <div>
              <p className="font-semibold text-foreground">macOS:</p>
              <p className="mb-1 text-xs">
                macOS may be blocking the bundled API binary. Run:
              </p>
              <pre className="rounded bg-muted p-2 text-xs">
                xattr -cr /Applications/VoidMelody.app
              </pre>
            </div>
            <div>
              <p className="font-semibold text-foreground">Windows / Linux:</p>
              <p className="text-xs">
                Ensure antivirus is not locking temp files and close any background instances, then click Restart API.
              </p>
            </div>
          </div>
        )}
      </div>
    );
  }

  if (preflightFailure) {
    const platformLabel = runtimePlatformLabel(preflightFailure);
    const diagnosticReport = formatPreflightFailure(preflightFailure);

    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 p-8 text-center text-destructive">
        <h2 className="text-xl font-bold">Desktop runtime check failed</h2>
        {platformLabel && <p className="text-sm font-semibold text-foreground">{platformLabel}</p>}
        {preflightFailure.missingEnv.length > 0 && (
          <div className="max-w-md text-left text-sm">
            <p className="font-semibold text-foreground">Thiếu environment do app inject</p>
            <ul className="mt-1 list-disc pl-5 font-mono">
              {preflightFailure.missingEnv.map((name) => <li key={name}>{name}</li>)}
            </ul>
          </div>
        )}
        {preflightFailure.missingResources.length > 0 && (
          <div className="max-w-md text-left text-sm">
            <p className="font-semibold text-foreground">Thiếu file trong installer</p>
            <ul className="mt-1 list-disc pl-5 font-mono">
              {preflightFailure.missingResources.map((name) => <li key={name}>{name}</li>)}
            </ul>
          </div>
        )}
        <button
          type="button"
          onClick={() => void navigator.clipboard?.writeText(diagnosticReport)}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
        >
          Copy diagnostic report
        </button>
      </div>
    );
  }

  if (!isReady) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-background">
        <Loader2 className="h-10 w-10 text-primary motion-safe:animate-spin" />
        <p className="text-sm font-medium text-muted-foreground">
          Starting local environment...
        </p>
      </div>
    );
  }

  return (
    <TauriContext.Provider value={contextValue}>
      {children}
    </TauriContext.Provider>
  );
}
