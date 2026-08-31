export let API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"
let API_TOKEN: string | null = null
let API_LICENSE_KEY: string | null = null

export function setApiBaseUrl(url: string) {
  API_BASE_URL = url
}

export function setApiConnection(url: string, token: string | null, licenseKey?: string | null) {
  API_BASE_URL = url
  API_TOKEN = token
  if (licenseKey !== undefined) {
    API_LICENSE_KEY = licenseKey
  }
}

export function setLicenseKey(key: string | null) {
  API_LICENSE_KEY = key
}

export function resolveApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`
}

function getEffectiveLicenseKey(): string | null {
  if (API_LICENSE_KEY) return API_LICENSE_KEY
  if (typeof window !== "undefined") {
    try {
      return localStorage.getItem("voidmelody_license_key")
    } catch {
      return null
    }
  }
  return null
}

export class ApiError extends Error {
  constructor(message: unknown, public status: number, public code?: string) {
    let readable = "Request failed"
    if (typeof message === "string") {
      readable = message
    } else if (message && typeof message === "object") {
      const obj = message as Record<string, unknown>
      readable = (obj.message as string) || (obj.detail as string) || (obj.code as string) || "Request failed"
    }
    super(readable)
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const isMultipart = typeof FormData !== "undefined" && init?.body instanceof FormData
  const headers: Record<string, string> = {
    ...(isMultipart ? {} : { "Content-Type": "application/json" }),
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (API_TOKEN) headers["X-Melody-Token"] = API_TOKEN
  const license = getEffectiveLicenseKey()
  if (license && !headers["X-License-Key"]) {
    headers["X-License-Key"] = license
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail ?? body?.message
    throw new ApiError(detail ?? "Request failed", response.status, body?.code ?? body?.error_code ?? detail?.code)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function apiFetchBlob(path: string, init?: RequestInit): Promise<Blob> {
  const headers: Record<string, string> = {}
  if (!(init?.body instanceof FormData)) headers["Content-Type"] = "application/json"
  Object.assign(headers, init?.headers as Record<string, string> | undefined)
  if (API_TOKEN) headers["X-Melody-Token"] = API_TOKEN
  const license = getEffectiveLicenseKey()
  if (license && !headers["X-License-Key"]) {
    headers["X-License-Key"] = license
  }
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail ?? body?.message
    throw new ApiError(
      detail ?? "Request failed",
      response.status,
      body?.code ?? body?.error_code ?? detail?.code,
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
