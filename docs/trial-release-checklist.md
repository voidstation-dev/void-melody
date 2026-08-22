# Trial release checklist

- Production Tauri launches the sidecar only after `trial_runtime` has
  reconciled Keychain/Credential Manager state and written the HMAC mirror.
- `MELODY_TRIAL_MODE=disabled` is honored only when `APP_ENV=development`.
- There is no production reset-trial command or UI.
- `TRIAL_EXPIRED`, `TRIAL_CLOCK_TAMPERED`, and `TRIAL_STATE_CORRUPTED` are
  returned as structured 403 responses for new compute requests.
- Existing audio routes remain read-only and available after expiry.
- Reinstall QA must verify the stable service/account pair
  `com.voidstation.melody.trial` / `trial-state-v1` on macOS Keychain and
  Windows Credential Manager.
- Support diagnostics may report status and remaining time, but never the
  integrity key, token, full script text, or credential payload.

The backend guard depends on the `EntitlementService` seam in
`app.services.trial_service`; a future paid/server entitlement can replace
the local implementation without changing every synthesis route.
