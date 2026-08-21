const { describe, it, beforeEach } = require("node:test");
const assert = require("node:assert/strict");
const FocusRestore = require("../wies/core/static/js/focus_restore.js");

// ─── Fake DOM ────────────────────────────────────────────────
//
// Only what FocusRestore touches. `takesFocus: false` is the case the module
// exists for: a custom element without delegatesFocus accepts focus() and then
// silently stays unfocused.

let doc;

const INVALID = "[invalid]:not(nldd-form-field-error-text)";
const AUTOFOCUS = "[autofocus]";

function element(attributes, options) {
  const opts = options || {};
  return {
    attributes: attributes || {},
    visible: opts.visible !== false,
    takesFocus: opts.takesFocus !== false,
    children: opts.children || [],
    focusCalls: [],
    getAttribute(name) {
      return name in this.attributes ? this.attributes[name] : null;
    },
    checkVisibility() {
      return this.visible;
    },
    contains(other) {
      return this.children.indexOf(other) !== -1;
    },
    focus(options) {
      this.focusCalls.push(options);
      if (this.takesFocus) doc.activeElement = this;
    },
  };
}

// A swap target. Rather than run a selector engine, it answers the three
// queries handleSettle makes from what the test declares it holds.
function swapTarget(content) {
  const held = content || {};
  const invalid = held.invalid || [];
  const autofocus = held.autofocus || [];
  const focusable = held.focusable || [];
  return {
    matches(selector) {
      return selector === AUTOFOCUS && held.selfAutofocus === true;
    },
    querySelector(selector) {
      const found = selector === AUTOFOCUS ? autofocus : focusable;
      return found.length ? found[0] : null;
    },
    querySelectorAll(selector) {
      return selector === INVALID ? invalid : focusable;
    },
  };
}

function makeDoc(elements) {
  return {
    body: { body: true },
    documentElement: { root: true },
    activeElement: null,
    elements: elements || [],
    querySelectorAll(selector) {
      const attribute = selector.slice(1, -1); // "[hx-get]" → "hx-get"
      return this.elements.filter((el) => el.getAttribute(attribute) !== null);
    },
  };
}

beforeEach(() => {
  doc = makeDoc();
});

// ─── describe ────────────────────────────────────────────────

describe("describe", () => {
  it("prefers the id", () => {
    const restore = new FocusRestore(doc);
    const found = restore.describe(element({ id: "save", "hx-get": "/panel" }));
    assert.deepEqual(found, { attribute: "id", value: "save" });
  });

  it("falls back through hx-get, hx-post and href", () => {
    const restore = new FocusRestore(doc);
    assert.deepEqual(restore.describe(element({ "hx-get": "/panel" })), {
      attribute: "hx-get",
      value: "/panel",
    });
    assert.deepEqual(restore.describe(element({ "hx-post": "/save" })), {
      attribute: "hx-post",
      value: "/save",
    });
    assert.deepEqual(restore.describe(element({ href: "/faq" })), {
      attribute: "href",
      value: "/faq",
    });
  });

  it("returns null without an identifying attribute", () => {
    const restore = new FocusRestore(doc);
    assert.equal(
      restore.describe(element({ class: "edit-icon-button" })),
      null,
    );
  });

  it("returns null for something that is not an element", () => {
    const restore = new FocusRestore(doc);
    assert.equal(restore.describe(null), null);
    assert.equal(restore.describe({}), null);
  });
});

// ─── remember ────────────────────────────────────────────────

describe("remember", () => {
  it("puts the newest entry first", () => {
    const restore = new FocusRestore(doc);
    restore.remember(element({ id: "first" }));
    restore.remember(element({ id: "second" }));
    assert.deepEqual(
      restore.trail.map((entry) => entry.value),
      ["second", "first"],
    );
  });

  it("caps the trail at maxDepth", () => {
    const restore = new FocusRestore(doc, { maxDepth: 3 });
    ["a", "b", "c", "d", "e"].forEach((id) =>
      restore.remember(element({ id })),
    );
    assert.deepEqual(
      restore.trail.map((entry) => entry.value),
      ["e", "d", "c"],
    );
  });

  it("ignores an element it cannot describe", () => {
    const restore = new FocusRestore(doc);
    restore.remember(element({ class: "x" }));
    restore.remember(null);
    assert.deepEqual(restore.trail, []);
  });
});

// ─── resolve ─────────────────────────────────────────────────

describe("resolve", () => {
  it("finds the element carrying that attribute value", () => {
    const wanted = element({ "hx-get": "/panel" });
    doc = makeDoc([element({ "hx-get": "/other" }), wanted]);
    const restore = new FocusRestore(doc);
    assert.equal(
      restore.resolve({ attribute: "hx-get", value: "/panel" }),
      wanted,
    );
  });

  it("skips the hidden duplicate in the overflow menu", () => {
    const hidden = element({ "hx-get": "/panel" }, { visible: false });
    const shown = element({ "hx-get": "/panel" });
    doc = makeDoc([hidden, shown]);
    const restore = new FocusRestore(doc);
    assert.equal(
      restore.resolve({ attribute: "hx-get", value: "/panel" }),
      shown,
    );
  });

  it("returns null when the element is gone", () => {
    doc = makeDoc([element({ "hx-get": "/other" })]);
    const restore = new FocusRestore(doc);
    assert.equal(
      restore.resolve({ attribute: "hx-get", value: "/panel" }),
      null,
    );
  });
});

// ─── focusTook ───────────────────────────────────────────────

describe("focusTook", () => {
  it("accepts the element itself and a descendant of it", () => {
    const inner = element({});
    const host = element({}, { children: [inner] });
    const restore = new FocusRestore(doc);

    doc.activeElement = host;
    assert.equal(restore.focusTook(host), true);

    doc.activeElement = inner;
    assert.equal(restore.focusTook(host), true);
  });

  it("rejects anything else", () => {
    const restore = new FocusRestore(doc);
    doc.activeElement = element({});
    assert.equal(restore.focusTook(element({})), false);
  });
});

// ─── focusFirst ──────────────────────────────────────────────

describe("focusFirst", () => {
  it("walks past a component that accepts focus() without taking it", () => {
    const refuses = element({}, { takesFocus: false });
    const accepts = element({});
    const restore = new FocusRestore(doc);

    assert.equal(restore.focusFirst([refuses, accepts]), true);
    assert.equal(doc.activeElement, accepts);
    assert.equal(refuses.focusCalls.length, 1);
  });

  it("skips an invisible element without calling focus", () => {
    const hidden = element({}, { visible: false });
    const shown = element({});
    const restore = new FocusRestore(doc);

    restore.focusFirst([hidden, shown]);
    assert.equal(hidden.focusCalls.length, 0);
    assert.equal(doc.activeElement, shown);
  });

  it("reports failure when nothing takes", () => {
    const restore = new FocusRestore(doc);
    assert.equal(
      restore.focusFirst([element({}, { takesFocus: false })]),
      false,
    );
    assert.equal(doc.activeElement, null);
  });

  it("prevents scrolling by default and not when told otherwise", () => {
    const first = element({});
    const second = element({});
    const restore = new FocusRestore(doc);

    restore.focusFirst([first]);
    assert.deepEqual(first.focusCalls, [{ preventScroll: true }]);

    restore.focusFirst([second], { preventScroll: false });
    assert.deepEqual(second.focusCalls, [{ preventScroll: false }]);
  });
});

// ─── focusFromTrail ──────────────────────────────────────────

describe("focusFromTrail", () => {
  it("returns to the newest entry it can find and drops what is newer", () => {
    const button = element({ id: "edit" });
    doc = makeDoc([button]);
    const restore = new FocusRestore(doc);
    restore.trail = [
      { attribute: "id", value: "gone" }, // the panel htmx fetched itself
      { attribute: "id", value: "edit" }, // the button we came from
      { attribute: "id", value: "older" },
    ];

    assert.equal(restore.focusFromTrail(), true);
    assert.equal(doc.activeElement, button);
    assert.deepEqual(
      restore.trail.map((entry) => entry.value),
      ["older"],
    );
  });

  it("keeps looking when an entry resolves but refuses focus", () => {
    const refuses = element({ id: "wrapper" }, { takesFocus: false });
    const accepts = element({ id: "edit" });
    doc = makeDoc([refuses, accepts]);
    const restore = new FocusRestore(doc);
    restore.trail = [
      { attribute: "id", value: "wrapper" },
      { attribute: "id", value: "edit" },
    ];

    assert.equal(restore.focusFromTrail(), true);
    assert.equal(doc.activeElement, accepts);
  });

  it("reports failure when the trail resolves to nothing", () => {
    doc = makeDoc([]);
    const restore = new FocusRestore(doc);
    restore.trail = [{ attribute: "id", value: "gone" }];
    assert.equal(restore.focusFromTrail(), false);
  });
});

// ─── handleSettle ────────────────────────────────────────────

describe("handleSettle", () => {
  it("sends everyone to the rejected field, mouse included, and scrolls to it", () => {
    const field = element({ invalid: "" });
    const restore = new FocusRestore(doc);
    restore.lastInput = "mouse";
    doc.activeElement = element({}); // focus survived somewhere else

    restore.handleSettle(swapTarget({ invalid: [field] }));

    assert.equal(doc.activeElement, field);
    assert.deepEqual(field.focusCalls, [{ preventScroll: false }]);
  });

  it("leaves focus alone when the mouse is driving", () => {
    const button = element({});
    const restore = new FocusRestore(doc);
    restore.lastInput = "mouse";

    restore.handleSettle(swapTarget({ focusable: [button] }));

    assert.equal(doc.activeElement, null);
    assert.equal(button.focusCalls.length, 0);
  });

  it("leaves focus alone when it survived the swap", () => {
    const searchField = element({});
    const button = element({});
    const restore = new FocusRestore(doc);
    doc.activeElement = searchField;

    restore.handleSettle(swapTarget({ focusable: [button] }));

    assert.equal(doc.activeElement, searchField);
    assert.equal(button.focusCalls.length, 0);
  });

  it("stays out of the way when the server set autofocus", () => {
    const autofocused = element({ autofocus: "" });
    const button = element({});
    const restore = new FocusRestore(doc);

    restore.handleSettle(
      swapTarget({ autofocus: [autofocused], focusable: [button] }),
    );

    assert.equal(button.focusCalls.length, 0);
  });

  it("stays out of the way when the container itself is the autofocus target", () => {
    const button = element({});
    const restore = new FocusRestore(doc);

    restore.handleSettle(
      swapTarget({ selfAutofocus: true, focusable: [button] }),
    );

    assert.equal(button.focusCalls.length, 0);
  });

  it("prefers the element that caused the swap over the first control", () => {
    const cause = element({ id: "edit" });
    const first = element({});
    doc = makeDoc([cause]);
    const restore = new FocusRestore(doc);
    restore.remember(cause);

    restore.handleSettle(swapTarget({ focusable: [first] }));

    assert.equal(doc.activeElement, cause);
    assert.equal(first.focusCalls.length, 0);
  });

  it("falls back to the first control when the cause is gone", () => {
    const first = element({});
    doc = makeDoc([]); // the button that caused the swap is no longer there
    const restore = new FocusRestore(doc);
    restore.trail = [{ attribute: "id", value: "gone" }];

    restore.handleSettle(swapTarget({ focusable: [first] }));

    assert.equal(doc.activeElement, first);
  });

  it("leaves focus on body when nothing in the new content takes it", () => {
    const refuses = element({}, { takesFocus: false });
    const restore = new FocusRestore(doc);

    restore.handleSettle(swapTarget({ focusable: [refuses] }));

    assert.equal(doc.activeElement, null);
  });

  it("does nothing for a target that is not an element", () => {
    const restore = new FocusRestore(doc);
    assert.doesNotThrow(() => restore.handleSettle(null));
    assert.doesNotThrow(() => restore.handleSettle({}));
  });
});
