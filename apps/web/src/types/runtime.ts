export type RuntimeStatus =
  | "missing"
  | "downloading"
  | "verifying"
  | "installing"
  | "ready"
  | "error"
  | "update_required"

export type RuntimeState = {
  id: string
  status: RuntimeStatus
  activeVersion: string | null
  installedVersions: string[]
  diskUsageBytes: number
  progress: number
  error: string | null
  protocolVersion: number | null
  probeResult: Record<string, unknown> | null
}