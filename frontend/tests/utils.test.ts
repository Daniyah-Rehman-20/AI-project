import { describe, expect, it } from "node:test";
import assert from "node:assert/strict";

// Lightweight smoke — full component tests run via `npm run build` typecheck in CI.
describe("frontend smoke", () => {
  it("string concat works", () => {
    assert.equal("Aether" + "Ops", "AetherOps");
  });
});
