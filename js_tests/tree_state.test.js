const { describe, it, beforeEach } = require("node:test");
const assert = require("node:assert/strict");
const TreeState = require("../wies/core/static/js/tree_state.js");

// ─── Test fixtures ───────────────────────────────────────────

// Simple 2-level tree:
//   A
//   ├── A1
//   └── A2
//   B
//   ├── B1
//   └── B2
function simpleTree() {
  return [
    {
      id: 1,
      label: "A",
      children: [
        { id: 2, label: "A1" },
        { id: 3, label: "A2" },
      ],
    },
    {
      id: 4,
      label: "B",
      children: [
        { id: 5, label: "B1" },
        { id: 6, label: "B2" },
      ],
    },
  ];
}

// 3-level tree:
//   Root
//   ├── Mid
//   │   ├── Leaf1
//   │   └── Leaf2
//   └── Mid2
//       └── Leaf3
function deepTree() {
  return [
    {
      id: "root",
      label: "Root",
      children: [
        {
          id: "mid",
          label: "Mid",
          children: [
            { id: "leaf1", label: "Leaf1" },
            { id: "leaf2", label: "Leaf2" },
          ],
        },
        {
          id: "mid2",
          label: "Mid2",
          children: [{ id: "leaf3", label: "Leaf3" }],
        },
      ],
    },
  ];
}

// Realistic tree with group and self nodes:
//   group-Ministerie (group)
//   ├── 10 Ministerie van Financien [MinFin]
//   │   ├── self-10 (self)
//   │   └── 11 Belastingdienst
//   │       └── 12 Afdeling IT
//   └── 20 Ministerie van BZK [BZK]
function realisticTree() {
  return [
    {
      id: "group-Ministerie",
      label: "Ministeries",
      group: true,
      children: [
        {
          id: 10,
          label: "Ministerie van Financien",
          abbreviations: ["MinFin"],
          children: [
            { id: "self-10", label: "Ministerie van Financien", self: true },
            {
              id: 11,
              label: "Belastingdienst",
              children: [{ id: 12, label: "Afdeling IT" }],
            },
          ],
        },
        { id: 20, label: "Ministerie van BZK", abbreviations: ["BZK"] },
      ],
    },
  ];
}

// ─── Tests ───────────────────────────────────────────────────

describe("TreeState construction", function () {
  it("indexes all nodes", function () {
    var ts = new TreeState(simpleTree());
    assert.equal(ts.nodes.size, 6);
    assert.ok(ts.getNode("1"));
    assert.ok(ts.getNode("6"));
  });

  it("converts numeric ids to strings", function () {
    var ts = new TreeState(simpleTree());
    assert.ok(ts.getNode("1"));
    assert.ok(ts.getNode(1));
  });

  it("sets parent references", function () {
    var ts = new TreeState(simpleTree());
    assert.equal(ts.getNode("2").parent, ts.getNode("1"));
    assert.equal(ts.getNode("1").parent, null);
  });

  it("handles empty data", function () {
    var ts = new TreeState([]);
    assert.equal(ts.nodes.size, 0);
    assert.equal(ts.roots.length, 0);
  });

  it("preserves group and self flags", function () {
    var ts = new TreeState(realisticTree());
    assert.equal(ts.getNode("group-Ministerie").group, true);
    assert.equal(ts.getNode("self-10").self, true);
    assert.equal(ts.getNode("10").group, false);
  });
});

describe("cascadeDown", function () {
  it("checking a leaf marks only that node", function () {
    var ts = new TreeState(simpleTree());
    ts.check("2");
    assert.equal(ts.getNode("2").checked, true);
    assert.equal(ts.getNode("3").checked, false);
    assert.equal(ts.getNode("5").checked, false);
  });

  it("checking a parent checks all descendants", function () {
    var ts = new TreeState(simpleTree());
    ts.check("1");
    assert.equal(ts.getNode("1").checked, true);
    assert.equal(ts.getNode("2").checked, true);
    assert.equal(ts.getNode("3").checked, true);
    // Other branch unaffected
    assert.equal(ts.getNode("4").checked, false);
  });

  it("unchecking a parent unchecks all descendants", function () {
    var ts = new TreeState(simpleTree());
    ts.check("1");
    ts.uncheck("1");
    assert.equal(ts.getNode("1").checked, false);
    assert.equal(ts.getNode("2").checked, false);
    assert.equal(ts.getNode("3").checked, false);
  });

  it("unchecking clears indeterminate on descendants", function () {
    var ts = new TreeState(deepTree());
    ts.check("leaf1"); // mid becomes indeterminate
    assert.equal(ts.getNode("mid").indeterminate, true);
    ts.uncheck("root"); // cascade down clears everything
    assert.equal(ts.getNode("mid").indeterminate, false);
    assert.equal(ts.getNode("leaf1").checked, false);
  });
});

describe("cascadeUp", function () {
  it("checking all siblings makes parent fully checked", function () {
    var ts = new TreeState(simpleTree());
    ts.check("2");
    ts.check("3");
    assert.equal(ts.getNode("1").checked, true);
    assert.equal(ts.getNode("1").indeterminate, false);
  });

  it("checking one sibling makes parent indeterminate", function () {
    var ts = new TreeState(simpleTree());
    ts.check("2");
    assert.equal(ts.getNode("1").checked, false);
    assert.equal(ts.getNode("1").indeterminate, true);
  });

  it("unchecking all siblings makes parent unchecked", function () {
    var ts = new TreeState(simpleTree());
    ts.check("2");
    ts.uncheck("2");
    assert.equal(ts.getNode("1").checked, false);
    assert.equal(ts.getNode("1").indeterminate, false);
  });

  it("propagates multiple levels up", function () {
    var ts = new TreeState(deepTree());
    ts.check("leaf1");
    // mid is indeterminate (leaf1 checked, leaf2 not)
    assert.equal(ts.getNode("mid").indeterminate, true);
    // root is indeterminate (mid indeterminate)
    assert.equal(ts.getNode("root").indeterminate, true);
  });

  it("checking all leaves makes entire ancestor chain fully checked", function () {
    var ts = new TreeState(deepTree());
    ts.check("leaf1");
    ts.check("leaf2");
    ts.check("leaf3");
    assert.equal(ts.getNode("mid").checked, true);
    assert.equal(ts.getNode("mid2").checked, true);
    assert.equal(ts.getNode("root").checked, true);
    assert.equal(ts.getNode("root").indeterminate, false);
  });
});

describe("explicitSelections", function () {
  it("checking a node adds it as explicit selection", function () {
    var ts = new TreeState(simpleTree());
    ts.check("2");
    assert.ok(ts.explicitSelections.has("2"));
    assert.equal(ts.explicitSelections.get("2"), "A1");
  });

  it("checking a parent removes descendant explicit selections", function () {
    var ts = new TreeState(simpleTree());
    ts.check("2");
    ts.check("1"); // A1 is now implied by A being checked
    assert.ok(ts.explicitSelections.has("1"));
    assert.ok(!ts.explicitSelections.has("2"));
  });

  it("unchecking a node removes it from explicit selections", function () {
    var ts = new TreeState(simpleTree());
    ts.check("2");
    ts.uncheck("2");
    assert.ok(!ts.explicitSelections.has("2"));
  });

  it("self-node labels include (direct)", function () {
    var ts = new TreeState(realisticTree());
    ts.check("self-10");
    assert.equal(
      ts.explicitSelections.get("self-10"),
      'Direct onder "Ministerie van Financien"',
    );
  });
});

describe("promote/demote", function () {
  it("unchecking child of explicit parent promotes remaining siblings", function () {
    var ts = new TreeState(simpleTree());
    ts.check("1"); // A explicit, A1+A2 checked
    ts.uncheck("2"); // uncheck A1
    // A is no longer explicit, A2 should be promoted
    assert.ok(!ts.explicitSelections.has("1"));
    assert.ok(ts.explicitSelections.has("3")); // A2 promoted
    assert.ok(!ts.explicitSelections.has("2")); // A1 was unchecked
  });

  it("promotion recurses through indeterminate children", function () {
    var ts = new TreeState(deepTree());
    ts.check("root"); // everything checked
    ts.uncheck("leaf1"); // mid becomes indeterminate
    // root was explicit, should be demoted
    // mid is indeterminate, so recurse: leaf2 is fully checked → promoted
    // mid2 is fully checked → promoted
    assert.ok(!ts.explicitSelections.has("root"));
    assert.ok(!ts.explicitSelections.has("mid"));
    assert.ok(ts.explicitSelections.has("leaf2"));
    assert.ok(ts.explicitSelections.has("mid2"));
  });

  it("demote works across multiple ancestor levels", function () {
    var ts = new TreeState(deepTree());
    ts.check("root");
    ts.uncheck("leaf3");
    // root demoted, mid fully checked → promoted, mid2 no longer checked
    assert.ok(!ts.explicitSelections.has("root"));
    assert.ok(ts.explicitSelections.has("mid"));
    assert.ok(!ts.explicitSelections.has("mid2"));
  });
});

describe("combined scenarios", function () {
  it("check parent, uncheck one child: parent gone, sibling explicit", function () {
    var ts = new TreeState(simpleTree());
    ts.check("1");
    ts.uncheck("3");
    assert.ok(!ts.explicitSelections.has("1"));
    assert.ok(ts.explicitSelections.has("2"));
    assert.equal(ts.explicitSelections.size, 1);
  });

  it("check two siblings individually, uncheck one: only other remains", function () {
    var ts = new TreeState(simpleTree());
    ts.check("2");
    ts.check("3");
    // Both siblings checked → parent becomes checked, but explicit selections
    // are 2 and 3 individually (not parent, since we checked children)
    // Actually: checking 3 after 2 means 3 is added. When all siblings are
    // checked, parent cascades up to checked. But explicitSelections still has
    // the individual ones since we didn't check parent directly.
    ts.uncheck("2");
    assert.ok(ts.explicitSelections.has("3"));
    assert.ok(!ts.explicitSelections.has("2"));
  });

  it("check leaf, then check parent: leaf subsumed by parent", function () {
    var ts = new TreeState(simpleTree());
    ts.check("2"); // A1 explicit
    ts.check("1"); // A explicit, A1 removed (implied)
    assert.ok(ts.explicitSelections.has("1"));
    assert.ok(!ts.explicitSelections.has("2"));
    assert.equal(ts.explicitSelections.size, 1);
  });

  it("removeSelection unchecks and cascades", function () {
    var ts = new TreeState(simpleTree());
    ts.check("1");
    ts.removeSelection("1");
    assert.equal(ts.getNode("1").checked, false);
    assert.equal(ts.getNode("2").checked, false);
    assert.equal(ts.getNode("3").checked, false);
    assert.equal(ts.explicitSelections.size, 0);
  });

  it("clearAll resets everything", function () {
    var ts = new TreeState(simpleTree());
    ts.check("1");
    ts.check("4");
    ts.clearAll();
    assert.equal(ts.explicitSelections.size, 0);
    ts.nodes.forEach(function (node) {
      assert.equal(node.checked, false);
      assert.equal(node.indeterminate, false);
    });
  });
});

describe("restoreSelections", function () {
  it("restores a single selection and cascades down", function () {
    var ts = new TreeState(simpleTree());
    ts.restoreSelections({ 1: "A" });
    assert.equal(ts.getNode("1").checked, true);
    assert.equal(ts.getNode("2").checked, true);
    assert.equal(ts.getNode("3").checked, true);
    assert.ok(ts.explicitSelections.has("1"));
  });

  it("restores multiple selections", function () {
    var ts = new TreeState(simpleTree());
    ts.restoreSelections({ 2: "A1", 5: "B1" });
    assert.equal(ts.getNode("2").checked, true);
    assert.equal(ts.getNode("5").checked, true);
    assert.equal(ts.getNode("3").checked, false);
    assert.equal(ts.getNode("1").indeterminate, true);
  });
});

describe("edge cases", function () {
  it("handles single-node tree", function () {
    var ts = new TreeState([{ id: 1, label: "Only" }]);
    ts.check("1");
    assert.equal(ts.getNode("1").checked, true);
    assert.ok(ts.explicitSelections.has("1"));
    ts.uncheck("1");
    assert.equal(ts.getNode("1").checked, false);
    assert.equal(ts.explicitSelections.size, 0);
  });

  it("check/uncheck on nonexistent node does nothing", function () {
    var ts = new TreeState(simpleTree());
    ts.check("999");
    ts.uncheck("999");
    assert.equal(ts.explicitSelections.size, 0);
  });

  it("handles string node IDs like self- and group-", function () {
    var ts = new TreeState(realisticTree());
    ts.check("self-10");
    assert.equal(ts.getNode("self-10").checked, true);
    assert.ok(ts.explicitSelections.has("self-10"));

    ts.check("group-Ministerie");
    assert.equal(ts.getNode("group-Ministerie").checked, true);
    assert.ok(ts.explicitSelections.has("group-Ministerie"));
    // self-10 should be subsumed (it's a descendant of group-Ministerie)
    assert.ok(!ts.explicitSelections.has("self-10"));
  });
});
