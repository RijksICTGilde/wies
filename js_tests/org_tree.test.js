const { describe, it, before } = require("node:test");
const assert = require("node:assert/strict");

// ─── Fake DOM ────────────────────────────────────────────────
//
// Only what OrgTree._buildRow touches. The point is the state the rows start
// in: their children are built on first expand, so a branch has none yet.

function fakeElement(tag) {
  return {
    tagName: tag.toUpperCase(),
    attributes: {},
    dataset: {},
    style: {},
    children: [],
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
    hasAttribute(name) {
      return name in this.attributes;
    },
    appendChild(child) {
      this.children.push(child);
      return child;
    },
    addEventListener() {},
  };
}

let OrgTree;

before(() => {
  global.document = { createElement: fakeElement };
  ({ OrgTree } = require("../wies/core/static/js/org_tree.js"));
});

function node(id, children) {
  return { id, label: id, children: children || [] };
}

function tree(selectable) {
  const orgTree = new OrgTree({
    state: { roots: [] },
    container: fakeElement("div"),
    isSelectable: () => selectable,
  });
  orgTree._syncRow = () => {};
  return orgTree;
}

describe("OrgTree._buildRow", () => {
  it("starts a branch closed, so its chevron reports collapsed", () => {
    for (const selectable of [true, false]) {
      const row = tree(selectable)._buildRow(node("tak", [node("blad")]), 0);
      assert.equal(row.expanded, false, `selectable=${selectable}`);
      // Lazy: the children are not there yet.
      assert.equal(row.dataset.childrenBuilt, undefined);
    }
  });

  it("leaves a leaf without an open/closed state", () => {
    const row = tree(true)._buildRow(node("blad"), 0);
    assert.equal(row.expanded, undefined);
  });
});
