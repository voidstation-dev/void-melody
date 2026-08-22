export type TrialStatusCode =
  | "ACTIVE"
  | "EXPIRING"
  | "EXPIRED"
  | "CLOCK_TAMPERED"
  | "CORRUPTED"

export type TrialStatus = {
  status: TrialStatusCode
  can_synthesize: boolean
  first_run_at: number | null
  expires_at: number | null
  remaining_seconds: number
  warning_level: "NONE" | "FORTY_EIGHT_HOURS" | "TWENTY_FOUR_HOURS" | "EXPIRED"
  override?: string | null
}
