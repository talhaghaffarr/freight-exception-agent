import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, expect, vi } from "vitest";
import { toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

// jsdom implements neither of these, and the shell measures both.
if (!window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as typeof window.matchMedia;
}

if (!window.ResizeObserver) {
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

/*
 * MapLibre creates its worker from a blob URL at import time, which jsdom does
 * not implement. The map itself is not under test here — the facts panels are —
 * so a stub is enough to let the module load.
 */
if (typeof window !== "undefined" && typeof window.URL.createObjectURL !== "function") {
  window.URL.createObjectURL = () => "blob:relayops-test";
  window.URL.revokeObjectURL = () => {};
}
