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
import { appDataDir, resolveResource } from "@tauri-apps/api/path";
import { Loader2 } from "lucide-react";
import { setApiConnection } from "@/lib/api-client";

type TauriContextValue = {
  isDesktop: boolean;
  isReady: boolean;
  shutdownSidecar: () => Promise<void>;
  restartSidecar: () => Promise<void>;
};

const TauriContext = createContext<TauriContextValue | null>(null);

function hasTauriRuntime() {
  return (
    typeof window !== "undefined" &&
    Boolean(
      (window as Window & { __TAURI_INTERNALS__?: unknown })
        .__TAURI_INTERNALS__,
    )
  );
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
  const mountedRef = useRef(false);
  const sidecarProcessRef = useRef<Child | null>(null);
  const startPromiseRef = useRef<Promise<void> | null>(null);
  const shutdownPromiseRef = useRef<Promise<void> | null>(null);
  const restartPromiseRef = useRef<Promise<void> | null>(null);

  const startSidecar = useCallback(() => {
    if (startPromiseRef.current) return startPromiseRef.current;

    const start = (async () => {
      const apiToken = crypto.randomUUID();
      const [dataDir, catalogPath] = await Promise.all([
        appDataDir(),
        resolveResource("bin/Voice.json"),
      ]);

      console.log("Starting sidecar with:", { dataDir, catalogPath });

      const sidecar = Command.sidecar("bin/melody-api", [], {
        env: {
          PYTHONUNBUFFERED: "1",
          APP_ENV: "production",
          API_HOST: "127.0.0.1",
          API_PORT: "0",
          MELODY_API_TOKEN: apiToken,
          MELODY_DATA_DIR: dataDir,
          MELODY_CATALOG_PATH: catalogPath,
          TTS_APPLY_RATE_WITH_FFMPEG: "true",
          TTS_QUEUE_CONCURRENCY: "1",
          TTS_CHUNK_CONCURRENCY: "1",
        },
      });

      let resolveReady: (() => void) | undefined;
      let rejectReady: ((reason: Error) => void) | undefined;
      let didResolve = false;
      const readyPromise = new Promise<void>((resolve, reject) => {
        resolveReady = resolve;
        rejectReady = reject;
      });

      // If the sidecar never prints a port (e.g. macOS Gatekeeper quarantines
      // the bundled binary and blocks its launch silently), the ready promise
      // would never settle and the UI would hang on "Starting local
      // environment..." forever. Time out so the user gets actionable guidance.
      const startupTimeoutMs = 15_000;
      const startupTimer = setTimeout(() => {
        if (didResolve || !mountedRef.current) return;
        rejectReady?.(new Error("Local API did not start in time"));
      }, startupTimeoutMs);

      const probeHealth = async (url: string) => {
        for (let attempt = 0; attempt < 10; attempt++) {
          try {
            const response = await fetch(`${url}/api/v1/health/live`, {
              method: "GET",
            });
            if (response.ok && mountedRef.current && !didResolve) {
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
          if (didResolve || !mountedRef.current) break;
          await new Promise((r) => setTimeout(r, 500));
        }
        return false;
      };

      const handleOutput = (line: string, source: "STDOUT" | "STDERR") => {
        console.log(`[API ${source}]:`, line);
        const match =
          line.match(
            /(?:https?:\/\/)?(?:127\.0\.0\.1|localhost|0\.0\.0\.0):(\d+)/,
          ) ?? line.match(/port\s+(\d+)/i);
        const port = match?.[1];
        if (port && port !== "0" && mountedRef.current) {
          console.log(`Resolved local API port from ${source}: ${port}`);
          void probeHealth(`http://127.0.0.1:${port}`);
        }
      };

      sidecar.stdout.on("data", (line) => handleOutput(line, "STDOUT"));
      sidecar.stderr.on("data", (line) => handleOutput(line, "STDERR"));

      const process = await sidecar.spawn();
      if (!mountedRef.current) {
        clearTimeout(startupTimer);
        await process.kill();
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
    const shutdown = process ? process.kill() : Promise.resolve();
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
      console.error("Failed to bootstrap Tauri sidecar", reason);
      if (mountedRef.current) {
        setError(String(reason));
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
    const isStartupTimeout = error.includes("did not start in time");
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 p-8 text-center text-destructive">
        <h2 className="text-xl font-bold">Failed to start local API</h2>
        <p className="font-mono text-sm">{error}</p>
        {isStartupTimeout && (
          <div className="max-w-md text-sm text-muted-foreground">
            <p className="mb-2">
              macOS may be blocking the bundled API binary. Open Terminal and
              run:
            </p>
            <pre className="rounded bg-muted p-2 text-left text-xs">
              xattr -cr /Applications/VoidMelody.app
            </pre>
            <p className="mt-2">Then relaunch the app.</p>
          </div>
        )}
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
