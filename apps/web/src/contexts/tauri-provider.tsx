import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react"
import { Command, type Child } from "@tauri-apps/plugin-shell"
import { appDataDir, resolveResource } from "@tauri-apps/api/path"
import { setApiConnection } from "@/lib/api-client"
import {
  BootstrapScreen,
  type BootstrapStage,
  type BootstrapStageId,
} from "@/components/bootstrap/bootstrap-screen"

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

const INITIAL_STAGES: BootstrapStage[] = [
  { id: "desktop", title: "Tauri Desktop Shell", detail: "Kiểm tra môi trường ứng dụng", status: "pending" },
  { id: "storage", title: "Storage & Audio Binaries", detail: "Đường dẫn AppData & FFmpeg", status: "pending" },
  { id: "sidecar", title: "Melody API Engine", detail: "Tiến trình Python Backend", status: "pending" },
  { id: "models", title: "VieNeu Neural Voice Models", detail: "Mô hình AI Voice & Tokenizer", status: "pending" },
  { id: "server", title: "HTTP Service & Gateway", detail: "Cổng kết nối máy chủ cục bộ", status: "pending" },
];

export function TauriProvider({ children }: { children: React.ReactNode }) {
  const [isDesktop, setIsDesktop] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stages, setStages] = useState<BootstrapStage[]>(INITIAL_STAGES);
  const [progressPercent, setProgressPercent] = useState(10);
  const [currentStatusText, setCurrentStatusText] = useState("Đang chuẩn bị môi trường...");
  const [liveLogs, setLiveLogs] = useState("");

  const mountedRef = useRef(false);
  const sidecarProcessRef = useRef<Child | null>(null);
  const startPromiseRef = useRef<Promise<void> | null>(null);
  const shutdownPromiseRef = useRef<Promise<void> | null>(null);
  const restartPromiseRef = useRef<Promise<void> | null>(null);

  const updateStage = useCallback((id: BootstrapStageId, status: BootstrapStage["status"], detail?: string) => {
    setStages((prev) =>
      prev.map((stage) =>
        stage.id === id
          ? { ...stage, status, ...(detail !== undefined ? { detail } : {}) }
          : stage,
      ),
    );
  }, []);

  const startSidecar = useCallback(() => {
    if (startPromiseRef.current) return startPromiseRef.current;

    const start = (async () => {
      updateStage("desktop", "completed", "Tauri 2 Shell sẵn sàng");
      updateStage("storage", "active", "Đang phân giải AppData & Voice.json...");
      setProgressPercent(20);
      setCurrentStatusText("Đang kiểm tra thư mục lưu trữ...");

      const apiToken = crypto.randomUUID();
      const [dataDir, catalogPath] = await Promise.all([
        appDataDir(),
        resolveResource("bin/Voice.json"),
      ]);

      console.log("Starting sidecar with:", { dataDir, catalogPath });
      updateStage("storage", "completed", "AppData & Catalog sẵn sàng");
      updateStage("sidecar", "active", "Đang khởi tạo tiến trình Python...");
      setProgressPercent(35);
      setCurrentStatusText("Khởi chạy tiến trình Python API...");

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
      let didReject = false;
      const readyPromise = new Promise<void>((resolve, reject) => {
        resolveReady = resolve;
        rejectReady = reject;
      });

      const startupTimeoutMs = 30_000;
      let startupTimer: ReturnType<typeof setTimeout>;

      const rejectStartup = (reason: Error) => {
        if (didResolve || didReject || !mountedRef.current) return;
        didReject = true;
        clearTimeout(startupTimer);
        rejectReady?.(reason);
      };

      const resetActivityTimer = (timeoutMs = 60_000) => {
        if (didResolve || didReject || !mountedRef.current) return;
        clearTimeout(startupTimer);
        startupTimer = setTimeout(
          () => rejectStartup(new Error("Local API did not start in time")),
          timeoutMs,
        );
      };

      startupTimer = setTimeout(
        () => rejectStartup(new Error("Local API did not start in time")),
        startupTimeoutMs,
      );

      const outputBuffers: Record<"STDOUT" | "STDERR", string> = {
        STDOUT: "",
        STDERR: "",
      };

      const recentSidecarOutput = () =>
        (["STDERR", "STDOUT"] as const)
          .map((source) => {
            const output = outputBuffers[source].trim();
            return output ? `${source}: ${output}` : "";
          })
          .filter(Boolean)
          .join("\n")
          .slice(-2_000);

      const probeHealth = async (url: string) => {
        updateStage("server", "active", `Đang xác thực ${url}...`);
        setCurrentStatusText(`Đang kết nối ${url}...`);
        for (let attempt = 0; attempt < 30; attempt++) {
          try {
            const response = await fetch(`${url}/api/v1/health/live`, {
              method: "GET",
            });
            if (response.ok && mountedRef.current && !didResolve && !didReject) {
              didResolve = true;
              clearTimeout(startupTimer);
              console.log(`Successfully connected to API at ${url}`);
              setApiConnection(url, apiToken);
              updateStage("models", "completed", "VieNeu AI Models sẵn sàng");
              updateStage("server", "completed", `Đã kết nối (${url})`);
              setProgressPercent(100);
              setCurrentStatusText("Môi trường đã sẵn sàng!");
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
        console.log(`[API ${source}]:`, line);
        resetActivityTimer();

        if (mountedRef.current) {
          setLiveLogs((prev) => {
            const updated = prev ? `${prev}\n${line}` : line;
            return updated.length > 8000 ? updated.slice(-8000) : updated;
          });
        }

        if (didResolve || didReject || !mountedRef.current) return;
        const normalizedLine = `${outputBuffers[source]}${line}`.replace(
          /\u001b\[[0-?]*[ -/]*[@-~]/g,
          "",
        );
        outputBuffers[source] = normalizedLine.slice(-1024);

        // Parse download / caching progress
        const fetchMatch = normalizedLine.match(/Fetching\s+(\d+)\s+files:\s*(\d+)%/i);
        if (fetchMatch) {
          const percent = Number(fetchMatch[2]);
          const scaledPercent = Math.min(85, Math.max(45, 45 + Math.round(percent * 0.4)));
          setProgressPercent(scaledPercent);
          updateStage("models", "active", `Đang tải files model (${percent}%)`);
          setCurrentStatusText(`Đang tải AI Voice Models (${percent}%)...`);
        } else if (/downloading|hf_hub_download|huggingface/i.test(normalizedLine)) {
          updateStage("models", "active", "Đang nạp file mô hình AI...");
          setProgressPercent((prev) => Math.max(prev, 55));
          setCurrentStatusText("Đang đồng bộ hóa VieNeu AI Model cache...");
        } else if (/Uvicorn running|Application startup complete|Listening on/i.test(normalizedLine)) {
          updateStage("models", "completed", "VieNeu AI Models sẵn sàng");
          updateStage("server", "active", "Đang kiểm tra cổng API...");
          setProgressPercent(90);
        }

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
      sidecar.on("error", (reason) => {
        const output = recentSidecarOutput();
        rejectStartup(
          new Error(
            `Sidecar process error: ${String(reason)}${output ? `\n${output}` : ""}`,
          ),
        );
      });
      sidecar.on("close", ({ code, signal }) => {
        const exitReason =
          code !== null && code !== undefined
            ? `exit code ${code}`
            : signal !== null && signal !== undefined
              ? `signal ${signal}`
              : "unknown reason";
        const output = recentSidecarOutput();
        rejectStartup(
          new Error(
            `Sidecar exited before API became ready (${exitReason})${output ? `\n${output}` : ""}`,
          ),
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
      updateStage("sidecar", "completed", `Process PID: ${process.pid}`);
      updateStage("models", "active", "Đang kiểm tra AI models...");
      setProgressPercent(45);
      setCurrentStatusText("Đang kiểm tra mô hình VieNeu AI...");

      return readyPromise;
    })();
    startPromiseRef.current = start.finally(() => {
      startPromiseRef.current = null;
    });
    return startPromiseRef.current;
  }, [updateStage]);

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
    setStages(INITIAL_STAGES);
    setProgressPercent(10);
    setCurrentStatusText("Đang khởi động lại môi trường...");
    setLiveLogs("");

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
      console.error("Failed to restart Tauri sidecar", reason);
      if (mountedRef.current) setError(String(reason));
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

  if (error || !isReady) {
    return (
      <BootstrapScreen
        stages={stages}
        progressPercent={progressPercent}
        currentStatusText={currentStatusText}
        logs={liveLogs}
        error={error}
        onRestart={error ? handleRestart : undefined}
      />
    );
  }

  return (
    <TauriContext.Provider value={contextValue}>
      {children}
    </TauriContext.Provider>
  );
}
