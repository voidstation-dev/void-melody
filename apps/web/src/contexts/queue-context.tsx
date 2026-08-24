import { createContext, ReactNode } from "react";
import { TTSJob } from "@/types/tts-job";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

type QueueContextType = {
  queue: TTSJob[];
  addToQueue: (jobs: TTSJob[]) => void;
  removeFromQueue: (jobId: string) => void;
  retryJob: (jobId: string) => void;
  clearQueue: () => void;
  refreshQueue: () => void;
  activeJobs: TTSJob[];
  completedJobs: TTSJob[];
};

type TTSJobListResponse = {
  items: TTSJob[];
  page: number;
  pageSize: number;
  total: number;
};

export const QueueContext = createContext<QueueContextType | undefined>(undefined);

export function QueueProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  const { data, refetch: refetchList } = useQuery({
    queryKey: ["tts-jobs-list"],
    queryFn: () => apiFetch<TTSJobListResponse>("/api/v1/tts/jobs?pageSize=50"),
    refetchInterval: (query) => {
      const items = query.state.data?.items;
      const hasActive = items?.some(
        (j) => j.status === "queued" || j.status === "processing"
      );
      return hasActive ? 1500 : false;
    },
  });

  const queue = (data?.items || []).slice().sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  );

  const addToQueue = (jobs: TTSJob[]) => {
    queryClient.setQueryData<TTSJobListResponse>(["tts-jobs-list"], (old) => {
      if (!old) {
        return { items: jobs, page: 1, pageSize: 50, total: jobs.length };
      }
      const existingIds = new Set(old.items.map((j) => j.id));
      const newItems = jobs.filter((j) => !existingIds.has(j.id));
      return {
        ...old,
        items: [...newItems, ...old.items],
        total: old.total + newItems.length,
      };
    });
    void refetchList();
  };

  const removeFromQueue = async (jobId: string) => {
    queryClient.setQueryData<TTSJobListResponse>(["tts-jobs-list"], (old) => {
      if (!old) return old;
      return { ...old, items: old.items.filter((j) => j.id !== jobId) };
    });

    try {
      await apiFetch(`/api/v1/tts/jobs/${jobId}`, {
        method: "DELETE",
      });
      void refetchList();
    } catch (error) {
      console.error("Failed to delete job:", error);
      void refetchList();
    }
  };

  const retryJob = async (jobId: string) => {
    try {
      await apiFetch(`/api/v1/tts/jobs/${jobId}/retry`, {
        method: "POST",
      });
      void refetchList();
    } catch (error) {
      console.error("Failed to retry job:", error);
    }
  };

  const clearQueue = () => {
    void refetchList();
  };

  const activeJobs = queue.filter(
    (j) => j.status === "processing" || j.status === "queued"
  );
  const completedJobs = queue.filter(
    (j) => j.status === "completed" || j.status === "failed"
  );

  return (
    <QueueContext.Provider
      value={{
        queue,
        addToQueue,
        removeFromQueue,
        retryJob,
        clearQueue,
        refreshQueue: () => void refetchList(),
        activeJobs,
        completedJobs,
      }}
    >
      {children}
    </QueueContext.Provider>
  );
}
