const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const { syncClampedToggle } = require("../wies/core/static/js/cv_clamp.js");

// The preview of parts/colleague_assignment_cards.html, with the sizes a
// browser would report for it, and the toggle the server rendered hidden.
function preview(scrollHeight, clientHeight, hidden) {
  return { scrollHeight, clientHeight, hidden: hidden === true };
}

describe("syncClampedToggle", () => {
  it("shows the toggle when the clamp cuts the text", () => {
    const toggle = { hidden: true };
    syncClampedToggle(preview(96, 72), toggle);
    assert.equal(toggle.hidden, false);
  });

  it("keeps the toggle hidden when the text fits", () => {
    const toggle = { hidden: true };
    syncClampedToggle(preview(48, 48), toggle);
    assert.equal(toggle.hidden, true);
  });

  it("hides it again when a wider screen makes the text fit", () => {
    const toggle = { hidden: false };
    syncClampedToggle(preview(72, 72), toggle);
    assert.equal(toggle.hidden, true);
  });

  it("leaves the toggle of an open entry alone", () => {
    // Open, the preview is hidden and measures 0; the toggle says "Toon minder".
    const toggle = { hidden: false };
    syncClampedToggle(preview(0, 0, true), toggle);
    assert.equal(toggle.hidden, false);
  });
});
