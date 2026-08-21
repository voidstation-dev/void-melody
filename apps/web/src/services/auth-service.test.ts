import { describe, expect, it } from "vitest";
import { verifyLicenseKey } from "./auth-service";
import { DEFAULT_DEV_KEY } from "@/constants";

describe("auth-service", () => {
  it("validates the default dev key successfully", async () => {
    const result = await verifyLicenseKey(DEFAULT_DEV_KEY, { simulatedDelayMs: 0 });
    expect(result.valid).toBe(true);
    expect(result.license).toBeDefined();
    expect(result.license?.key).toBe(DEFAULT_DEV_KEY);
    expect(result.license?.ownerName).toBe("Phong Vũ");
  });

  it("handles case-insensitive and trimmed key entry", async () => {
    const result = await verifyLicenseKey("  PHONGVU  ", { simulatedDelayMs: 0 });
    expect(result.valid).toBe(true);
    expect(result.license?.key).toBe(DEFAULT_DEV_KEY);
  });

  it("rejects an empty key", async () => {
    const result = await verifyLicenseKey("", { simulatedDelayMs: 0 });
    expect(result.valid).toBe(false);
    expect(result.error).toBe("KEY_EMPTY");
  });

  it("rejects an invalid key", async () => {
    const result = await verifyLicenseKey("wrong-key-123", { simulatedDelayMs: 0 });
    expect(result.valid).toBe(false);
    expect(result.error).toBe("INVALID_KEY");
  });
});
