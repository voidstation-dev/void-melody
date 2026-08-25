import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api-client"
import type { RuntimeState } from "@/types/runtime"

export async function fetchRuntimes(): Promise<RuntimeState[]> {
  const res = await apiFetch<{ items: RuntimeState[] }>("/api/v1/runtimes")
  return res.items
}

export async function fetchRuntimeStatus(id: string): Promise<RuntimeState> {
  return apiFetch<RuntimeState>(`/api/v1/runtimes/${id}/status`)
}

export async function installRuntime(id: string, file: File): Promise<RuntimeState> {
  const form = new FormData()
  form.append("file", file)
  return apiFetch<RuntimeState>(`/api/v1/runtimes/${id}/install`, {
    method: "POST",
    body: form,
  })
}

export async function updateRuntime(id: string, file: File): Promise<RuntimeState> {
  const form = new FormData()
  form.append("file", file)
  return apiFetch<RuntimeState>(`/api/v1/runtimes/${id}/update`, {
    method: "POST",
    body: form,
  })
}

export async function repairRuntime(id: string): Promise<RuntimeState> {
  return apiFetch<RuntimeState>(`/api/v1/runtimes/${id}/repair`, { method: "POST" })
}

export async function removeRuntime(id: string): Promise<void> {
  await apiFetch<{ id: string; removed: boolean }>(`/api/v1/runtimes/${id}`, {
    method: "DELETE",
  })
}

export async function rollbackRuntime(id: string): Promise<RuntimeState> {
  return apiFetch<RuntimeState>(`/api/v1/runtimes/${id}/rollback`, { method: "POST" })
}

export function useRuntimes() {
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: ["runtimes"],
    queryFn: fetchRuntimes,
    staleTime: 30 * 1000,
    gcTime: 60 * 1000,
  })

  const install = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => installRuntime(id, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["runtimes"] }),
  })

  const update = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => updateRuntime(id, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["runtimes"] }),
  })

  const repair = useMutation({
    mutationFn: repairRuntime,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["runtimes"] }),
  })

  const remove = useMutation({
    mutationFn: removeRuntime,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["runtimes"] }),
  })

  const rollback = useMutation({
    mutationFn: rollbackRuntime,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["runtimes"] }),
  })

  return { query, install, update, repair, remove, rollback }
}