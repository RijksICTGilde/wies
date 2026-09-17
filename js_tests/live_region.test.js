const { describe, it, beforeEach } = require("node:test");
const assert = require("node:assert/strict");
const LiveRegion = require("../wies/core/static/js/live_region.js");

// ─── Fake DOM ────────────────────────────────────────────────
//
// Only what LiveRegion touches: a container answers the three selectors with
// what the test declares it holds, the document hands out the region.

let doc, region, alertRegion, timers;

function el(attributes, text) {
  return {
    getAttribute(name) {
      return name in attributes ? attributes[name] : null;
    },
    matches(selector) {
      return selector === "nldd-notification[text]" && "text" in attributes;
    },
    querySelectorAll: () => [],
    textContent: text || "",
  };
}

function container(held) {
  const byselector = {
    "nldd-notification[text]": held.notifications || [],
    "[data-announce]": held.announce || [],
    "nldd-form-field-error-text": held.errors || [],
  };
  return {
    matches: () => false,
    querySelectorAll: (selector) => byselector[selector] || [],
  };
}

function makeDoc(notifications, sheets) {
  return {
    readyState: "complete",
    body: {
      appended: [],
      appendChild(node) {
        this.appended.push(node);
        node.parentElement = this;
      },
    },
    getElementById(id) {
      if (id === "wies-live") return region;
      if (id === "wies-alert") return alertRegion;
      return null;
    },
    querySelectorAll(selector) {
      if (selector === "nldd-notification[text]") return notifications || [];
      if (selector === "nldd-sheet") return sheets || [];
      return [];
    },
    createElement() {
      return {
        attributes: {},
        setAttribute(name, value) {
          this.attributes[name] = value;
        },
      };
    },
  };
}

// A sheet: a host with a shadow dialog that is modal or not, and a light-DOM
// child list that the live region is appended to.
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

beforeEach(() => {
  region = { textContent: "" };
  alertRegion = {
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
  timers = [];
  doc = makeDoc();
});

function liveRegion(options) {
  let clock = 0;
  return new LiveRegion(doc, {
    setTimeout: (fn, ms) => timers.push({ fn, ms }),
    now: () => (options && options.now ? options.now() : (clock += 1)),
  });
}

// ─── messagesIn ──────────────────────────────────────────────

describe("messagesIn", () => {
  it("reads the count a list carries", () => {
    const live = liveRegion();
    const found = live.messagesIn(
      container({ announce: [el({ "data-announce": "12 gebruikers" })] }),
    );
    assert.deepEqual(found, ["12 gebruikers"]);
  });

  it("folds the errors of a rejected form into one sentence", () => {
    const live = liveRegion();
    const found = live.messagesIn(
      container({
        errors: [
          el({}, " Opdrachtnaam is verplicht "),
          el({}, "Voeg minimaal 1 opdrachtgever toe"),
        ],
      }),
    );
    assert.deepEqual(found, [
      "Het formulier heeft 2 fouten: Opdrachtnaam is verplicht. Voeg minimaal 1 opdrachtgever toe",
    ]);
  });

  it("leaves errors inside a role=alert to that alert", () => {
    const live = liveRegion();
    const alerted = el({}, "Al gemeld");
    alerted.closest = (selector) => (selector === "[role='alert']" ? {} : null);
    const found = live.messagesIn(
      container({ errors: [alerted, el({}, "Vul een naam in")] }),
    );
    assert.deepEqual(found, ["Het formulier heeft 1 fout: Vul een naam in"]);
  });

  it("says fout, not fouten, for a single error", () => {
    const live = liveRegion();
    const found = live.messagesIn(
      container({ errors: [el({}, "Vul een naam in")] }),
    );
    assert.deepEqual(found, ["Het formulier heeft 1 fout: Vul een naam in"]);
  });

  it("includes the container itself when it is the list", () => {
    const live = liveRegion();
    const list = container({});
    list.matches = (selector) => selector === "[data-announce]";
    list.getAttribute = () => "Geen opdrachten gevonden";
    assert.deepEqual(live.messagesIn(list), ["Geen opdrachten gevonden"]);
  });

  it("returns nothing for a fragment with nothing to say, or no element", () => {
    const live = liveRegion();
    assert.deepEqual(live.messagesIn(container({})), []);
    assert.deepEqual(live.messagesIn(null), []);
    assert.deepEqual(live.messagesIn({}), []);
  });
});

// ─── announce ────────────────────────────────────────────────

describe("announce", () => {
  it("empties the region and fills it a tick later", () => {
    const live = liveRegion();
    region.textContent = "6 collega's";

    assert.equal(live.announce("6 collega's"), true);
    assert.equal(region.textContent, "");
    assert.equal(timers.length, 1);
    timers[0].fn();
    assert.equal(region.textContent, "6 collega's");
  });

  it("drops the same text heard again within the window", () => {
    let clock = 0;
    const live = liveRegion({ now: () => clock });
    assert.equal(live.announce("6 collega's"), true);
    clock = 500;
    assert.equal(live.announce("6 collega's"), false);
    clock = 1500;
    assert.equal(live.announce("6 collega's"), true);
  });

  it("does nothing without a region or without text", () => {
    region = null;
    const live = liveRegion();
    assert.equal(live.announce("x"), false);
    region = { textContent: "" };
    assert.equal(live.announce(""), false);
  });
});

// ─── handleSettle / handleLoad ───────────────────────────────

describe("handleSettle", () => {
  it("announces what the settled fragment carries, in reading order", () => {
    const live = liveRegion();
    live.handleSettle(
      container({
        announce: [el({ "data-announce": "3 opdrachten" })],
        errors: [el({}, "Vul een naam in")],
      }),
    );
    timers[0].fn();
    assert.equal(
      region.textContent,
      "3 opdrachten. Het formulier heeft 1 fout: Vul een naam in",
    );
  });

  it("stays quiet for a fragment with nothing to say", () => {
    const live = liveRegion();
    assert.equal(live.handleSettle(container({})), false);
    assert.equal(timers.length, 0);
  });
});

describe("modal sheet", () => {
  it("prepares an empty region in every sheet, once", () => {
    const open = sheet(true);
    doc = makeDoc([], [open]);
    const live = liveRegion();
    live.prepareSheets();
    live.prepareSheets();
    assert.equal(open.children.length, 1);
    assert.equal(open.children[0].attributes.role, "status");
  });

  it("reads out inside the modal sheet, and in the body otherwise", () => {
    const modal = sheet(true);
    const plain = sheet(false);
    doc = makeDoc([], [plain, modal]);
    const live = liveRegion();
    live.prepareSheets();
    assert.equal(live.region(), modal.children[0]);

    doc = makeDoc([], [plain]);
    const live2 = liveRegion();
    live2.prepareSheets();
    assert.equal(live2.region(), region);
  });

  it("raises the notification region above a modal sheet as a popover, every time", () => {
    const modal = sheet(true);
    const calls = [];
    const notifications = {
      attributes: {},
      style: {},
      open: false,
      getAttribute(name) {
        return this.attributes[name] || null;
      },
      setAttribute(name, value) {
        this.attributes[name] = value;
      },
      matches(selector) {
        return selector === ":popover-open" && this.open;
      },
      showPopover() {
        this.open = true;
        calls.push("show");
      },
      hidePopover() {
        this.open = false;
        calls.push("hide");
      },
    };
    doc = makeDoc([], [modal]);
    doc.getElementById = (id) =>
      id === "nldd-notification-region" ? notifications : region;
    const live = liveRegion();
    live.raiseNotifications();
    assert.equal(notifications.attributes.popover, "manual");
    assert.equal(notifications.style.margin, "0");
    assert.deepEqual(calls, ["show"]);

    live.raiseNotifications();
    assert.deepEqual(
      calls,
      ["show", "hide", "show"],
      "restacked above a dialog opened since",
    );
  });

  it("leaves the notification region alone without a modal sheet", () => {
    const notifications = {
      setAttribute() {
        throw new Error("touched");
      },
      showPopover() {},
    };
    doc = makeDoc([], [sheet(false)]);
    doc.getElementById = (id) =>
      id === "nldd-notification-region" ? notifications : region;
    liveRegion().raiseNotifications();
  });
});

describe("handleNotifications", () => {
  it("announces the text of a notification that entered the document", () => {
    const live = liveRegion();
    live.handleNotifications([el({ text: "Opdrachtnaam opgeslagen" }), {}]);
    timers[0].fn();
    assert.equal(region.textContent, "Opdrachtnaam opgeslagen");
  });

  it("finds the notifications inside an added wrapper, like the flash block", () => {
    const live = liveRegion();
    const wrapper = el({});
    wrapper.querySelectorAll = () => [el({ text: "Merk is toegevoegd." })];
    live.handleNotifications([wrapper]);
    timers[0].fn();
    assert.equal(region.textContent, "Merk is toegevoegd.");
  });

  it("reads a notification once when it is added and moved in one batch", () => {
    const live = liveRegion();
    live.handleNotifications([
      el({ text: "Opgeslagen" }),
      el({ text: "Opgeslagen" }),
    ]);
    timers[0].fn();
    assert.equal(region.textContent, "Opgeslagen");
  });

  it("swallows the second arrival when the component moves itself", () => {
    const live = liveRegion();
    live.handleNotifications([el({ text: "Opgeslagen" })]);
    assert.equal(
      live.handleNotifications([el({ text: "Opgeslagen" })]),
      undefined,
    );
    assert.equal(timers.length, 1);
  });

  it("ignores nodes without text", () => {
    const live = liveRegion();
    live.handleNotifications([el({ text: "  " }), null]);
    assert.equal(timers.length, 0);
  });
});

describe("watchNotifications", () => {
  it("watches the whole document and reads a notification that is added", () => {
    const observed = [];
    doc = makeDoc();
    function FakeObserver(callback) {
      this.observe = (node, options) =>
        observed.push({ node, options, callback });
    }
    const live = new LiveRegion(doc, {
      setTimeout: (fn, ms) => timers.push({ fn, ms }),
      MutationObserver: FakeObserver,
    });
    live.watchNotifications();
    assert.equal(observed.length, 1);
    assert.equal(observed[0].node, doc.body);
    assert.deepEqual(observed[0].options, { childList: true, subtree: true });

    observed[0].callback([
      { addedNodes: [el({ text: "Periode opgeslagen" })] },
    ]);
    timers[0].fn();
    assert.equal(region.textContent, "Periode opgeslagen");
  });

  it("does nothing where there is no MutationObserver", () => {
    doc = makeDoc();
    const live = new LiveRegion(doc, {
      setTimeout: () => {},
      MutationObserver: null,
    });
    live.watchNotifications();
  });
});

describe("handleLoad", () => {
  it("gives a flash message that came with the page focus, after a delay", () => {
    doc = makeDoc([el({ text: "Gebruiker verwijderd" })]);
    const live = liveRegion();
    live.handleLoad();

    assert.equal(timers.length, 1);
    assert.equal(timers[0].ms, 1000);
    timers[0].fn();
    assert.equal(alertRegion.textContent, "Gebruiker verwijderd");
    assert.equal(alertRegion.attributes.tabindex, "-1");
    assert.deepEqual(alertRegion.focusCalls, [{ preventScroll: true }]);
    assert.equal(
      region.textContent,
      "",
      "not the polite region: that is not spoken after a load",
    );
  });

  it("keeps the watcher off the notifications it will announce itself", () => {
    doc = makeDoc([el({ text: "Je naam is opgeslagen." })]);
    let clock = 0;
    const live = liveRegion({ now: () => clock });
    live.handleLoad();
    // The component moves the notification into its region: the watcher sees
    // it arrive, and must not say it politely now, or the alert later is a repeat.
    live.handleNotifications([el({ text: "Je naam is opgeslagen." })]);
    assert.equal(timers.length, 1, "no polite announcement queued");
    timers[0].fn();
    assert.equal(alertRegion.textContent, "Je naam is opgeslagen.");
    assert.equal(region.textContent, "");

    clock = 5000;
    live.handleNotifications([el({ text: "Je naam is opgeslagen." })]);
    assert.equal(
      timers.length,
      2,
      "after the load, the same words are a new notification again",
    );
  });

  it("does nothing without flash messages", () => {
    doc = makeDoc([]);
    liveRegion().handleLoad();
    assert.equal(timers.length, 0);
  });
});
