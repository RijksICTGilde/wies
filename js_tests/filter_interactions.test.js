const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const {
  forwardViewChange,
} = require("../wies/core/static/js/filter_interactions.js");

// Fake of parts/view_control.html; the component sets `value` before change.

function item(value) {
  return {
    localName: "nldd-segmented-control-item",
    getAttribute: (name) => (name === "value" ? value : null),
  };
}

function control(value, options) {
  const opts = options || {};
  const items = [item("persoon"), item("opdracht")];
  return {
    localName: opts.localName || "nldd-segmented-control",
    value: value,
    items: items,
    closest: (selector) =>
      selector === "#view-control" && opts.inViewControl !== false ? {} : null,
    querySelectorAll: () => items,
  };
}

function fakeHtmx() {
  const calls = [];
  return { calls, trigger: (el, name) => calls.push({ el, name }) };
}

describe("forwardViewChange", () => {
  it("triggers the chosen item once (arrow keys and click alike)", () => {
    const el = control("opdracht");
    const htmx = fakeHtmx();

    forwardViewChange({ target: el }, htmx);

    assert.equal(htmx.calls.length, 1);
    assert.equal(htmx.calls[0].el, el.items[1]);
    assert.equal(htmx.calls[0].name, "wies-view-change");
  });

  it("ignores a segmented control outside the view switch", () => {
    const htmx = fakeHtmx();

    forwardViewChange(
      { target: control("opdracht", { inViewControl: false }) },
      htmx,
    );

    assert.equal(htmx.calls.length, 0);
  });

  it("ignores change events from other elements", () => {
    const htmx = fakeHtmx();

    forwardViewChange(
      { target: control("opdracht", { localName: "nldd-list-item" }) },
      htmx,
    );
    forwardViewChange({ target: null }, htmx);

    assert.equal(htmx.calls.length, 0);
  });

  it("does nothing when no item has the control's value", () => {
    const htmx = fakeHtmx();

    forwardViewChange({ target: control("onbekend") }, htmx);

    assert.equal(htmx.calls.length, 0);
  });
});
