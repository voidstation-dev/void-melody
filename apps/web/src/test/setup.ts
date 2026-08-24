import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import React from "react";

if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as typeof ResizeObserver;
}

if (typeof HTMLElement !== "undefined" && !HTMLElement.prototype.scrollIntoView) {
  HTMLElement.prototype.scrollIntoView = () => {};
}

vi.mock("@tanstack/react-router", async () => {
  const actual = await vi.importActual<Record<string, any>>("@tanstack/react-router");
  return {
    ...actual,
    Link: React.forwardRef<HTMLAnchorElement, any>(function MockLink(
      { to, href, children, activeProps, inactiveProps, search, ...props },
      ref,
    ) {
      let targetHref = to || href || "#";
      if (search && typeof search === "object") {
        const searchParams = new URLSearchParams();
        for (const [k, v] of Object.entries(search)) {
          if (v !== undefined && v !== null) {
            searchParams.set(k, String(v));
          }
        }
        const qs = searchParams.toString();
        if (qs) {
          targetHref = `${targetHref}${targetHref.includes("?") ? "&" : "?"}${qs}`;
        }
      }
      return React.createElement(
        "a",
        {
          ref,
          href: typeof targetHref === "string" ? targetHref : "#",
          ...props,
        },
        children,
      );
    }),
    useSearch: () => ({}),
    useNavigate: () => vi.fn(),
    useLocation: () => ({ pathname: "/" }),
    useRouter: () => ({
      state: { location: { pathname: "/" } },
      navigate: vi.fn(),
      isServer: false,
    }),
  };
});

afterEach(() => {
  cleanup();
});
