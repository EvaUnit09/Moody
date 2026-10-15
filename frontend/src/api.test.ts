import { afterEach, describe, expect, test, vi } from "vitest";
import { recommend } from "./api";

function respondWith(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status })),
  );
}

describe("api error messages", () => {
  afterEach(() => vi.unstubAllGlobals());

  test("shows the rate-limit message from a 429 body", async () => {
    respondWith(429, {
      error: "Rate limit exceeded",
      message: "You've made too many requests. Please try again in a minute.",
    });

    await expect(recommend({ query: "cozy" })).rejects.toThrow(
      "You've made too many requests. Please try again in a minute.",
    );
  });

  test("falls back to the status when detail is a validation list", async () => {
    respondWith(422, { detail: [{ loc: ["body", "exclude_tmdb_ids"], msg: "too long" }] });

    await expect(recommend({ query: "cozy" })).rejects.toThrow(
      "Request failed with status 422",
    );
  });

  test("shows a string detail", async () => {
    respondWith(503, { detail: "Database busy, try again shortly" });

    await expect(recommend({ query: "cozy" })).rejects.toThrow(
      "Database busy, try again shortly",
    );
  });
});
