const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const { panelEntry } = require("../wies/core/static/js/side_panel.js");

const ORIGIN = "http://localhost";

describe("panelEntry", () => {
  it("is the entry when it is a panel", () => {
    for (const url of [
      "/?opdracht=1",
      "/?collega=2",
      "/opdrachten/?aanvraag=3",
      "/opdrachten/?nieuwe-opdracht=1",
    ]) {
      const entry = { url, title: "Paneel" };
      assert.equal(panelEntry(entry, ORIGIN), entry, url);
    }
  });

  it("is nothing for the page under the panel", () => {
    // A sheet opened from a card on Mijn profiel has no panel to go back to:
    // its back button would only close it.
    assert.equal(panelEntry({ url: "/profiel/", title: "" }, ORIGIN), null);
    assert.equal(panelEntry({ url: "/?pagina=2", title: "" }, ORIGIN), null);
  });

  it("is nothing without an entry", () => {
    assert.equal(panelEntry(undefined, ORIGIN), null);
    assert.equal(panelEntry(null, ORIGIN), null);
  });
});

describe("parentUrlOf", () => {
  const { parentUrlOf } = require("../wies/core/static/js/side_panel.js");
  const at = (path) => new URL(path, ORIGIN);

  it("is the panel under a sheet loaded straight from its URL", () => {
    assert.equal(
      parentUrlOf(at("/opdrachten/?opdracht=1&bewerken=1")),
      "/opdrachten/?opdracht=1",
    );
    assert.equal(
      parentUrlOf(at("/?opdracht=1&collega=2&teamlid=3")),
      "/?opdracht=1&collega=2",
    );
  });

  it("is nothing for a panel itself or a page without one", () => {
    assert.equal(parentUrlOf(at("/?opdracht=1")), null);
    assert.equal(parentUrlOf(at("/profiel/?bewerken=1")), null);
  });
});
