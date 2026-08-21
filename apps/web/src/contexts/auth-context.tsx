"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { STORAGE_KEYS } from "@/constants";
import { verifyLicenseKey, LicenseInfo } from "@/services/auth-service";

export interface AuthContextType {
  isAuthenticated: boolean;
  licenseKey: string | null;
  licenseInfo: LicenseInfo | null;
  isLoading: boolean;
  login: (key: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({
  children,
  initialKey,
}: {
  children: React.ReactNode;
  initialKey?: string | null;
}) {
  const [licenseKey, setLicenseKey] = useState<string | null>(initialKey ?? null);
  const [licenseInfo, setLicenseInfo] = useState<LicenseInfo | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Restore saved license key from storage on initial mount
  useEffect(() => {
    let mounted = true;

    async function initAuth() {
      let savedKey: string | null = initialKey ?? null;
      if (!savedKey && typeof window !== "undefined") {
        try {
          savedKey = localStorage.getItem(STORAGE_KEYS.AUTH_KEY);
        } catch {
          // localStorage access error
        }
      }

      if (savedKey) {
        const result = await verifyLicenseKey(savedKey, { simulatedDelayMs: 0 });
        if (mounted) {
          if (result.valid && result.license) {
            setLicenseKey(savedKey);
            setLicenseInfo(result.license);
            setIsAuthenticated(true);
          } else {
            // Key is invalid or expired, clear storage
            try {
              localStorage.removeItem(STORAGE_KEYS.AUTH_KEY);
            } catch {}
            setLicenseKey(null);
            setLicenseInfo(null);
            setIsAuthenticated(false);
          }
        }
      }

      if (mounted) {
        setIsLoading(false);
      }
    }

    void initAuth();

    return () => {
      mounted = false;
    };
  }, [initialKey]);

  const login = useCallback(async (key: string): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);
    try {
      const result = await verifyLicenseKey(key);
      if (result.valid && result.license) {
        setLicenseKey(result.license.key);
        setLicenseInfo(result.license);
        setIsAuthenticated(true);
        if (typeof window !== "undefined") {
          try {
            localStorage.setItem(STORAGE_KEYS.AUTH_KEY, result.license.key);
          } catch {}
        }
        return { success: true };
      } else {
        return { success: false, error: result.error ?? "INVALID_KEY" };
      }
    } catch {
      return { success: false, error: "NETWORK_ERROR" };
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setLicenseKey(null);
    setLicenseInfo(null);
    setIsAuthenticated(false);
    if (typeof window !== "undefined") {
      try {
        localStorage.removeItem(STORAGE_KEYS.AUTH_KEY);
      } catch {}
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        licenseKey,
        licenseInfo,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
