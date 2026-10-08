const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const {
  toggleLongText,
  toggleCard,
} = require("../wies/core/static/js/ui_handlers.js");

// ─── Fake DOM ────────────────────────────────────────────────
//
// Only what the toggles touch. The point of these tests is that the selectors
// keep matching the markup the templates render: toggle-long-text once looked
// for a wrapper class no template produced, so the button did nothing at all
// and no test noticed (#693).

function element(className, options) {
  const opts = options || {};
  return {
    className: className,
    hidden: opts.hidden === true,
    attributes: {},
    parent: null,
    children: opts.children || [],
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
    getAttribute(name) {
      return name in this.attributes ? this.attributes[name] : null;
    },
    toggleAttribute(name, force) {
      if (force) this.attributes[name] = "";
      else delete this.attributes[name];
    },
    hasAttribute(name) {
      return name in this.attributes;
    },
    closest(selector) {
      const wanted = selector.replace(".", "");
      let node = this;
      while (node) {
        if (node.className === wanted) return node;
        node = node.parent;
      }
      return null;
    },
    querySelector(selector) {
      const wanted = selector.replace(".", "");
      return descendants(this).find((n) => n.className === wanted) || null;
    },
  };
}

function descendants(node) {
  return node.children.flatMap((child) => [child, ...descendants(child)]);
}

function tree(root) {
  for (const child of root.children) {
    child.parent = root;
    tree(child);
  }
  return root;
}

// The markup of forms/displays/textarea.html: a truncated and a full copy,
// one of them hidden, with the toggle beside them.
function longText() {
  const truncated = element("inline-edit-long-text__truncated");
  const full = element("inline-edit-long-text__full", { hidden: true });
  const toggle = element("inline-edit-show-more");
  const wrapper = tree(
    element("inline-edit-long-text", { children: [truncated, full, toggle] }),
  );
  return { wrapper, truncated, full, toggle };
}

// The markup of parts/colleague_assignment_cards.html: a preview and a
// details block, one of them hidden, inside one cv entry.
function cvEntry() {
  const preview = element("wies-cv__preview");
  const more = element("wies-cv__more", { hidden: true });
  const toggle = element("wies-cv__toggle");
  const entry = tree(
    element("wies-cv__item", { children: [preview, more, toggle] }),
  );
  return { entry, preview, more, toggle };
}

describe("toggle-long-text (a description folded to its first lines)", () => {
  it("swaps the truncated copy for the full one", () => {
    const { truncated, full, toggle } = longText();

    toggleLongText(toggle);

    assert.equal(full.hidden, false, "the full text should be shown");
    assert.equal(truncated.hidden, true, "the truncated copy should be hidden");
  });

  it("folds it back on a second click", () => {
    const { truncated, full, toggle } = longText();

    toggleLongText(toggle);
    toggleLongText(toggle);

    assert.equal(full.hidden, true);
    assert.equal(truncated.hidden, false);
  });

  it("says what it will do and what it did", () => {
    const { toggle } = longText();

    toggleLongText(toggle);
    assert.equal(toggle.getAttribute("text"), "Toon minder");
    assert.equal(toggle.getAttribute("start-icon"), "chevron-up");
    // nldd-button forwards `expanded` as aria-expanded: a screen reader has to
    // hear the state, not just the label.
    assert.ok(
      toggle.hasAttribute("expanded"),
      "expanded should be set when open",
    );

    toggleLongText(toggle);
    assert.equal(toggle.getAttribute("text"), "Toon meer");
    assert.equal(toggle.getAttribute("start-icon"), "chevron-down");
    assert.ok(
      !toggle.hasAttribute("expanded"),
      "expanded should be dropped when closed",
    );
  });

  it("does nothing when the toggle sits outside the wrapper it expects", () => {
    // The regression itself: a toggle whose markup does not match returns
    // quietly instead of throwing, so only an assertion like this catches it.
    const stray = element("inline-edit-show-more");

    assert.doesNotThrow(() => toggleLongText(stray));
    assert.equal(stray.getAttribute("text"), null);
  });
});

describe("toggle-card (an opdracht entry in a colleague's cv list)", () => {
  it("opens the details and hides the preview", () => {
    const { preview, more, toggle } = cvEntry();

    toggleCard(toggle);

    assert.equal(more.hidden, false);
    assert.equal(preview.hidden, true);
    assert.equal(toggle.getAttribute("text"), "Toon minder");
    assert.ok(toggle.hasAttribute("expanded"));
  });

  it("closes again and restores the preview", () => {
    const { preview, more, toggle } = cvEntry();

    toggleCard(toggle);
    toggleCard(toggle);

    assert.equal(more.hidden, true);
    assert.equal(preview.hidden, false);
    assert.equal(toggle.getAttribute("text"), "Toon meer");
    assert.ok(!toggle.hasAttribute("expanded"));
  });
});
