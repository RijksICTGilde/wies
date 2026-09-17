const { describe, it, beforeEach } = require("node:test");
const assert = require("node:assert/strict");
const LiveRegion = require("../wies/core/static/js/live_region.js");

// ─── Fake DOM ────────────────────────────────────────────────
//
// Only what LiveRegion touches: elements answer getAttribute and matches, a
// container answers the three selectors with what the test declares it holds,
// the document hands out the regions and the sheets.

let doc, region, alertRegion, timers, clock;

function el(attributes, text) {
  return {
    getAttribute: (name) => (name in attributes ? attributes[name] : null),
    matches: (selector) =>
      selector === "nldd-notification[text]" && "text" in attributes,
    querySelectorAll: () => [],
    textContent: text || "",
  };
}

function container(held) {
  const bySelector = {
    "[data-announce]": held.announce || [],
    "[invalid][unmet]": held.rejected || [],
  };
  return {
    matches: () => false,
    querySelectorAll: (selector) => bySelector[selector] || [],
  };
}

// A sheet: a host with a shadow dialog that is modal or not, and a light-DOM
// child list that the region is appended to.
function sheet(modal) {
  return {
    children: [],
    shadowRoot: {
      querySelector: () => ({
        matches: (selector) => selector === ":modal" && modal,
      }),
    },
    querySelector(selector) {
      return selector === "[data-wies-live]" ? this.children[0] || null : null;
    },
    appendChild(node) {
      this.children.push(node);
      node.parentElement = this;
    },
  };
}

function focusable() {
  return {
    textContent: "",
    attributes: {},
    focusCalls: [],
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
    focus(options) {
      this.focusCalls.push(options);
    },
  };
}

beforeEach(() => {
  region = { textContent: "" };
  alertRegion = focusable();
  timers = [];
  clock = 0;
  doc = {
    readyState: "complete",
    body: {},
    notifications: [],
    sheets: [],
    items: {},
    getElementById(id) {
      return (
        { "wies-live": region, "wies-alert": alertRegion }[id] ||
        this.items[id] ||
        null
      );
    },
    querySelectorAll(selector) {
      if (selector === "nldd-notification[text]") return this.notifications;
      if (selector === "nldd-sheet") return this.sheets;
      return [];
    },
    createElement: () => focusable(),
  };
});

function live(options) {
  return new LiveRegion(doc, {
    setTimeout: (fn, ms) => timers.push({ fn, ms }),
    now: () => clock,
    ...options,
  });
}

// ─── messagesIn ──────────────────────────────────────────────

describe("messagesIn", () => {
  it("reads the count a list carries, then the errors the rejected controls point at", () => {
    doc.items = {
      "e-name": el({}, " Opdrachtnaam is verplicht "),
      "e-org": el({}, "Voeg minimaal 1 opdrachtgever toe"),
    };
    const found = live().messagesIn(
      container({
        announce: [el({ "data-announce": "12 gebruikers" })],
        // The picker's wrapper and its button name the same id: read once.
        rejected: [
          el({ unmet: "e-name" }),
          el({ unmet: "e-org" }),
          el({ unmet: "e-org" }),
        ],
      }),
    );
    assert.deepEqual(found, [
      "12 gebruikers",
      "Het formulier heeft 2 fouten: Opdrachtnaam is verplicht. Voeg minimaal 1 opdrachtgever toe",
    ]);
  });

  it("says fout for a single error and skips ids without an item", () => {
    doc.items = { "e-name": el({}, "Vul een naam in") };
    const found = live().messagesIn(
      container({ rejected: [el({ unmet: "e-name e-gone" })] }),
    );
    assert.deepEqual(found, ["Het formulier heeft 1 fout: Vul een naam in"]);
  });

  it("includes the container itself when it is the list", () => {
    const list = container({});
    list.matches = (selector) => selector === "[data-announce]";
    list.getAttribute = () => "Geen opdrachten gevonden";
    assert.deepEqual(live().messagesIn(list), ["Geen opdrachten gevonden"]);
  });

  it("returns nothing for a fragment with nothing to say, or no element", () => {
    assert.deepEqual(live().messagesIn(container({})), []);
    assert.deepEqual(live().messagesIn(null), []);
  });
});

// ─── announce ────────────────────────────────────────────────

describe("announce", () => {
  it("empties the region and fills it a tick later, so a repeat is still a change", () => {
    region.textContent = "6 collega's";
    assert.equal(live().announce("6 collega's"), true);
    assert.equal(region.textContent, "");
    timers[0].fn();
    assert.equal(region.textContent, "6 collega's");
  });

  it("drops the same text heard again within the window", () => {
    const l = live();
    assert.equal(l.announce("6 collega's"), true);
    clock = 500;
    assert.equal(l.announce("6 collega's"), false);
    clock = 1500;
    assert.equal(l.announce("6 collega's"), true);
  });

  it("does nothing without a region or without text", () => {
    region = null;
    assert.equal(live().announce("x"), false);
    region = { textContent: "" };
    assert.equal(live().announce(""), false);
  });
});

// ─── modal sheet ─────────────────────────────────────────────

describe("modal sheet", () => {
  it("prepares one region per sheet and reads out in the modal one, else in the body", () => {
    const modal = sheet(true);
    doc.sheets = [sheet(false), modal];
    const l = live();
    l.prepareSheets();
    l.prepareSheets();
    assert.equal(modal.children.length, 1);
    assert.equal(modal.children[0].attributes.role, "status");
    assert.equal(l.region(), modal.children[0]);

    doc.sheets = [sheet(false)];
    assert.equal(live().region(), region);
  });
});

// ─── notifications ───────────────────────────────────────────

describe("notifications", () => {
  it("tells NLDD about a sheet that was modal before the first notification", () => {
    const modal = sheet(true);
    const events = [];
    modal.contains = () => false;
    modal.dispatchEvent = (e) => events.push([e.type, e.bubbles]);
    doc.sheets = [modal];
    doc.getElementById = (id) =>
      id === "nldd-notification-region" ? {} : region;
    live().nudgeNotifications();
    assert.deepEqual(events, [["open", true]]);

    modal.contains = () => true;
    live().nudgeNotifications();
    assert.equal(
      events.length,
      1,
      "already inside the sheet: nothing to nudge",
    );
  });

  it("reads a notification once, nested in a wrapper or added and moved in one batch", () => {
    const wrapper = el({});
    wrapper.querySelectorAll = () => [el({ text: "Merk is toegevoegd." })];
    live().handleNotifications([
      wrapper,
      el({ text: "Merk is toegevoegd." }),
      {},
    ]);
    timers[0].fn();
    assert.equal(region.textContent, "Merk is toegevoegd.");
    assert.equal(timers.length, 1);
  });

  it("watches the whole document and does nothing where there is no MutationObserver", () => {
    const observed = [];
    function FakeObserver(callback) {
      this.observe = (node, options) =>
        observed.push({ node, options, callback });
    }
    live({ MutationObserver: FakeObserver }).watchNotifications();
    assert.equal(observed[0].node, doc.body);
    assert.deepEqual(observed[0].options, { childList: true, subtree: true });
    observed[0].callback([
      { addedNodes: [el({ text: "Periode opgeslagen" })] },
    ]);
    timers[0].fn();
    assert.equal(region.textContent, "Periode opgeslagen");

    live({ MutationObserver: null }).watchNotifications();
  });
});

// ─── page load ───────────────────────────────────────────────

describe("handleLoad", () => {
  it("gives a flash message that came with the page focus, and keeps the watcher off it", () => {
    doc.notifications = [el({ text: "Je naam is opgeslagen." })];
    const l = live();
    l.handleLoad();
    // The component moves the notification into its region: the watcher sees
    // it arrive and must stay quiet, or the message is heard twice.
    l.handleNotifications([el({ text: "Je naam is opgeslagen." })]);
    assert.equal(timers.length, 1);
    assert.equal(timers[0].ms, 1000);
    timers[0].fn();
    assert.equal(alertRegion.textContent, "Je naam is opgeslagen.");
    assert.equal(alertRegion.attributes.tabindex, "-1");
    assert.deepEqual(alertRegion.focusCalls, [{ preventScroll: true }]);
    assert.equal(
      region.textContent,
      "",
      "not the polite region: that is not spoken after a load",
    );

    clock = 5000;
    l.handleNotifications([el({ text: "Je naam is opgeslagen." })]);
    assert.equal(
      timers.length,
      2,
      "after the load, the same words are a new notification again",
    );
  });

  it("does nothing without flash messages", () => {
    live().handleLoad();
    assert.equal(timers.length, 0);
  });
});
