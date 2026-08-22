# Trial synthesis inventory

This matrix is the TR-00 scope for the local 7-day beta gate. The API remains
the enforcement authority; frontend locks are only explanatory UX.

| Surface | Entry point | Classification after expiry |
| --- | --- | --- |
| Standard single TTS | `POST /api/v1/tts/jobs` | Block new synthesis |
| Standard batch TTS | `POST /api/v1/tts/jobs/batch`, `POST /api/v1/tts/batches` | Block new synthesis |
| Standard preview | `POST /api/v1/tts/preview` | Block new synthesis |
| Custom voice enrollment | `POST /api/v1/tts/voices/clone` | Block model compute |
| Emotional Script render | `POST /api/v1/scripts/{script_id}/renders` | Block new synthesis |
| Emotional Script retry/regenerate | `POST /api/v1/script-renders/{render_id}/retry` | Block manual retry |
| Emotional Script line preview | `POST /api/v1/scripts/{script_id}/lines/{line_id}/preview` | Block if it synthesizes |
| Standard queue worker | `execute_tts_job_step` | Accepted jobs may finish |
| Emotional Script queue worker | `execute_script_render` | Accepted renders may finish |
| Provider-direct calls | queue/provider adapters | Only reachable from an accepted job |
| Existing audio playback | `GET .../audio` | Allow |
| Existing audio download/export | `GET .../download`, export routes | Allow |
| History, scripts, settings, voice browsing | read/write metadata routes | Allow |

## Accepted-work policy

At request acceptance the API records an authorization timestamp on the job or
render. Workers do not re-check the trial for that already-accepted operation,
so a render that crosses the expiration boundary remains deterministic. Manual
retry is a new compute request and is checked again.
