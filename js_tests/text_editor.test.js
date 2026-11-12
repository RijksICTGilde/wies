const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const {
  listOf,
  headingText,
  inlineToRun,
} = require("../wies/core/static/js/text_editor.js");

describe("inlineToRun", () => {
  it("runs only the keys whose state has to change", () => {
    const wanted = new Set(["bold", "italic"]);
    const active = { bold: true, italic: false, strikethrough: true };
    assert.deepEqual(inlineToRun(wanted, active), ["italic", "strikethrough"]);
  });

  it("runs nothing when the group already matches the editor", () => {
    const active = { bold: true, italic: false, strikethrough: false };
    assert.deepEqual(inlineToRun(new Set(["bold"]), active), []);
  });

  it("treats a key the state leaves out as off", () => {
    assert.deepEqual(inlineToRun(new Set(["bold"]), {}), ["bold"]);
  });
});

describe("listOf", () => {
  it("names the list the caret is in", () => {
    assert.equal(listOf({ orderedList: true }), "ordered");
    assert.equal(listOf({ bulletList: true }), "bullet");
    assert.equal(listOf({}), "none");
  });
});

describe("headingText", () => {
  it("reads a paragraph as Paragraaf", () => {
    assert.equal(headingText(0), "Paragraaf");
    assert.equal(headingText(undefined), "Paragraaf");
  });

  it("reads a typed level-4 heading as Kop 4, not as Kop 3", () => {
    assert.equal(headingText(2), "Kop 2");
    assert.equal(headingText(4), "Kop 4");
  });
});
