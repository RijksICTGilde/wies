const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const { syncClampedToggle } = require("../wies/core/static/js/cv_clamp.js");

// A clamped preview with the sizes a browser would report for it, and its
// "Toon meer" button; `expanded` is the attribute an open toggle carries.
function preview(scrollHeight, clientHeight) {
  return { scrollHeight, clientHeight };
}

function toggle(hidden, expanded) {
  return {
    hidden,
    hasAttribute: (name) => name === "expanded" && expanded === true,
  };
}

describe("syncClampedToggle", () => {
  it("shows the toggle when the clamp cuts the text", () => {
    const button = toggle(true);
    syncClampedToggle(preview(96, 72), button);
    assert.equal(button.hidden, false);
  });

  it("keeps the toggle hidden when the text fits", () => {
    const button = toggle(true);
    syncClampedToggle(preview(48, 48), button);
    assert.equal(button.hidden, true);
  });

  it("hides it again when a wider screen makes the text fit", () => {
    const button = toggle(false);
    syncClampedToggle(preview(72, 72), button);
    assert.equal(button.hidden, true);
  });

  it("leaves the toggle of an open text alone", () => {
    // Open, nothing is clamped (a cv preview is even hidden and measures 0);
    // the toggle says "Toon minder".
    const button = toggle(false, true);
    syncClampedToggle(preview(0, 0), button);
    assert.equal(button.hidden, false);
  });
});
