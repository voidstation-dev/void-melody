import { DEFAULT_DEV_KEY } from "@/constants";

export interface LicenseInfo {
  key: string;
  ownerName?: string;
  tier?: string;
  activatedAt?: string;
  expiresAt?: string;
}

export interface VerifyKeyResult {
  valid: boolean;
  error?: string;
  license?: LicenseInfo;
}

/**
 * Validates an access key / license key.
 * Currently simulates authentication against the default evaluation key ("phongvu").
 * When an external API endpoint is configured, it will dispatch an HTTP verification request.
 */
export async function verifyLicenseKey(
  rawKey: string,
  options: { simulatedDelayMs?: number } = {},
): Promise<VerifyKeyResult> {
  const { simulatedDelayMs = 400 } = options;

  const key = rawKey.trim();

  // Simulate network latency for realistic micro-interactions
  if (simulatedDelayMs > 0) {
    await new Promise((resolve) => setTimeout(resolve, simulatedDelayMs));
  }

  if (!key) {
    return {
      valid: false,
      error: "KEY_EMPTY",
    };
  }

  // Check if an external verification endpoint is configured
  const authApiUrl = import.meta.env.VITE_AUTH_API_URL;
  if (authApiUrl) {
    try {
      const res = await fetch(`${authApiUrl}/v1/license/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key }),
      });
      if (!res.ok) {
        return {
          valid: false,
          error: "INVALID_KEY",
        };
      }
      const data = await res.json();
      return {
        valid: true,
        license: {
          key,
          ownerName: data.ownerName ?? "Licensed User",
          tier: data.tier ?? "Pro",
          activatedAt: data.activatedAt ?? new Date().toISOString(),
          expiresAt: data.expiresAt,
        },
      };
    } catch (err) {
      console.warn("External auth API verification failed, falling back to mock validator:", err);
    }
  }

  // Default Mock Evaluation Rule
  if (key.toLowerCase() === DEFAULT_DEV_KEY.toLowerCase()) {
    return {
      valid: true,
      license: {
        key: DEFAULT_DEV_KEY,
        ownerName: "Phong Vũ",
        tier: "Lifetime Pro License",
        activatedAt: new Date().toISOString(),
      },
    };
  }

  return {
    valid: false,
    error: "INVALID_KEY",
  };
}
