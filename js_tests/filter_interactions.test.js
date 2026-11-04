const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const {
  shouldForward,
} = require("../wies/core/static/js/filter_interactions.js");

// The date filter refreshes the list; these decide when typing may trigger it.
describe("shouldForward", () => {
  it("skips an event whose value did not move", () => {
    assert.equal(
      shouldForward("2026-12-01", "2026-12-01", "01-12-2026"),
      false,
    );
  });

  it("forwards a new value", () => {
    assert.equal(shouldForward("", "2026-12-01", "01-12-2026"), true);
  });

  it("keeps a date being corrected: empty value, text still in the field", () => {
    assert.equal(shouldForward("2026-12-01", "", "01-12-20"), false);
  });

  it("forwards a cleared field", () => {
    assert.equal(shouldForward("2026-12-01", "", ""), true);
  });
});
