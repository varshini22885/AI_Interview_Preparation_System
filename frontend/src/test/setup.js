import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

beforeEach(() => {
  // Every test starts from a KNOWN fetch mock. Individual tests replace it
  // with scenario stubs via stubBackend(); the default fails loudly instead
  // of hitting the network.
  const fallback = vi.fn(async () => {
    throw new Error("fetch is not mocked in this test");
  });
  vi.stubGlobal("fetch", fallback);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
