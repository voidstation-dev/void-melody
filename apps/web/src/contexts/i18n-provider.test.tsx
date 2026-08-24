// @vitest-environment jsdom

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { I18nProvider, useTranslation } from "./i18n-provider";

function TestComponent() {
  const { t, locale, setLocale, isVi, isEn } = useTranslation();

  return (
    <div>
      <span data-testid="current-locale">{locale}</span>
      <span data-testid="is-vi">{isVi ? "yes" : "no"}</span>
      <span data-testid="is-en">{isEn ? "yes" : "no"}</span>
      <h1 data-testid="nav-generate">{t("nav.generate")}</h1>
      <p data-testid="char-count">{t("generate.charCount", { count: 125 })}</p>
      <button onClick={() => setLocale("en")}>Switch to English</button>
      <button onClick={() => setLocale("vi")}>Switch to Vietnamese</button>
    </div>
  );
}

describe("I18nProvider", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("defaults to Vietnamese locale", () => {
    render(
      <I18nProvider>
        <TestComponent />
      </I18nProvider>,
    );

    expect(screen.getByTestId("current-locale")).toHaveTextContent("vi");
    expect(screen.getByTestId("is-vi")).toHaveTextContent("yes");
    expect(screen.getByTestId("is-en")).toHaveTextContent("no");
    expect(screen.getByTestId("nav-generate")).toHaveTextContent("Tạo audio");
    expect(screen.getByTestId("char-count")).toHaveTextContent("125 ký tự");
  });

  it("switches to English and updates translations & document lang", () => {
    render(
      <I18nProvider>
        <TestComponent />
      </I18nProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Switch to English" }));

    expect(screen.getByTestId("current-locale")).toHaveTextContent("en");
    expect(screen.getByTestId("is-vi")).toHaveTextContent("no");
    expect(screen.getByTestId("is-en")).toHaveTextContent("yes");
    expect(screen.getByTestId("nav-generate")).toHaveTextContent("Audio Studio");
    expect(screen.getByTestId("char-count")).toHaveTextContent("125 characters");
    expect(localStorage.getItem("voidmelody_locale")).toBe("en");
    expect(document.documentElement.lang).toBe("en");
  });

  it("loads saved locale from localStorage on initial render", () => {
    localStorage.setItem("voidmelody_locale", "en");

    render(
      <I18nProvider>
        <TestComponent />
      </I18nProvider>,
    );

    expect(screen.getByTestId("current-locale")).toHaveTextContent("en");
    expect(screen.getByTestId("nav-generate")).toHaveTextContent("Audio Studio");
  });
});
