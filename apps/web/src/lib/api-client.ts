export let API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
let API_TOKEN: string | null = null

export function setApiBaseUrl(url: string) {
  API_BASE_URL = url
}

export function setApiConnection(url: string, token: string | null) {
  API_BASE_URL = url
  API_TOKEN = token
}

export function resolveApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`
}
export class ApiError extends Error {
  constructor(message: string, public status: number, public code?: string) {
    super(message)
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (API_TOKEN) headers["X-Melody-Token"] = API_TOKEN
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(body?.detail ?? "Request failed", response.status, body?.code)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function apiFetchBlob(path: string): Promise<Blob> {
  const headers: Record<string, string> = {}
  if (API_TOKEN) headers["X-Melody-Token"] = API_TOKEN
  const response = await fetch(`${API_BASE_URL}${path}`, { headers })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(
      body?.detail ?? "Request failed",
      response.status,
      body?.code,
    )
  }
  return response.blob()
}

export async function exportJobAudio(jobId: string, format: string, path: string): Promise<{ status: string; path: string }> {
  return apiFetch<{ status: string; path: string }>(`/api/v1/tts/jobs/${jobId}/export`, {
    method: "POST",
    body: JSON.stringify({ exportPath: path, exportFormat: format }),
  })
}
