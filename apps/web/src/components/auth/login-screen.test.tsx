// @vitest-environment jsdom

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";
import { LoginScreen } from "./login-screen";
import { AuthProvider } from "@/contexts/auth-context";
import { I18nProvider } from "@/contexts/i18n-provider";
import { DEFAULT_DEV_KEY } from "@/constants";

function renderLoginScreen() {
  return render(
    <I18nProvider initialLocale="vi">
      <AuthProvider>
        <LoginScreen />
      </AuthProvider>
    </I18nProvider>
  );
}

describe("LoginScreen", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders activation form fields and branding", async () => {
    renderLoginScreen();

    expect(screen.getByText("Kích hoạt Void Melody")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Nhập khóa bản quyền (ví dụ: phongvu)…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Xác nhận & Kích hoạt/i })).toBeInTheDocument();
  });

  it("shows error message when entering an invalid key", async () => {
    renderLoginScreen();

    const input = screen.getByPlaceholderText("Nhập khóa bản quyền (ví dụ: phongvu)…");
    fireEvent.change(input, { target: { value: "invalid-key" } });

    const submitBtn = screen.getByRole("button", { name: /Xác nhận & Kích hoạt/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
    expect(screen.getByText("Khóa bản quyền không hợp lệ hoặc đã hết hạn. Vui lòng kiểm tra lại.")).toBeInTheDocument();
  });

  it("fills input when clicking the demo key helper", async () => {
    renderLoginScreen();

    const demoBtn = screen.getByText("Khóa kích hoạt dùng thử mặc định: phongvu");
    fireEvent.click(demoBtn);

    const input = screen.getByPlaceholderText("Nhập khóa bản quyền (ví dụ: phongvu)…") as HTMLInputElement;
    expect(input.value).toBe(DEFAULT_DEV_KEY);
  });
});
