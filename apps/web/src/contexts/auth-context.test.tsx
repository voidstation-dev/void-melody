// @vitest-environment jsdom

import React from "react";
import { render, screen, act, waitFor } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";
import { AuthProvider, useAuth } from "./auth-context";
import { STORAGE_KEYS, DEFAULT_DEV_KEY } from "@/constants";

function TestConsumer() {
  const { isAuthenticated, licenseKey, login, logout, isLoading } = useAuth();
  return (
    <div>
      <span data-testid="loading">{isLoading ? "loading" : "ready"}</span>
      <span data-testid="auth-status">{isAuthenticated ? "logged-in" : "logged-out"}</span>
      <span data-testid="license-key">{licenseKey ?? "none"}</span>
      <button onClick={() => login(DEFAULT_DEV_KEY)}>Login Valid</button>
      <button onClick={() => login("bad-key")}>Login Invalid</button>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

describe("AuthContext", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("starts in unauthenticated state when no key is stored", async () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("ready");
    });
    expect(screen.getByTestId("auth-status").textContent).toBe("logged-out");
  });

  it("auto-authenticates when a valid key is in localStorage", async () => {
    localStorage.setItem(STORAGE_KEYS.AUTH_KEY, DEFAULT_DEV_KEY);

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("ready");
    });
    expect(screen.getByTestId("auth-status").textContent).toBe("logged-in");
    expect(screen.getByTestId("license-key").textContent).toBe(DEFAULT_DEV_KEY);
  });

  it("logs in with valid key and persists to localStorage", async () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("ready");
    });

    await act(async () => {
      screen.getByText("Login Valid").click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("auth-status").textContent).toBe("logged-in");
    });
    expect(localStorage.getItem(STORAGE_KEYS.AUTH_KEY)).toBe(DEFAULT_DEV_KEY);
  });

  it("logs out and clears localStorage", async () => {
    localStorage.setItem(STORAGE_KEYS.AUTH_KEY, DEFAULT_DEV_KEY);

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("auth-status").textContent).toBe("logged-in");
    });

    act(() => {
      screen.getByText("Logout").click();
    });

    expect(screen.getByTestId("auth-status").textContent).toBe("logged-out");
    expect(localStorage.getItem(STORAGE_KEYS.AUTH_KEY)).toBeNull();
  });
});
