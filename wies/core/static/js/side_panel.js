// Side panel on the nldd-sheet API: panel stack for back navigation, URL sync
// and popstate.

(function () {
  "use strict";

  const SHEET_ID = "side-panel";
  const CONTENT_ID = "side-panel-content";
  // The params that open a panel: their presence means "a panel belongs here".
  const PANEL_PARAMS = ["collega", "opdracht", "aanvraag", "nieuwe-opdracht"];

  function hasPanelParam(url) {
    return PANEL_PARAMS.some((name) => url.searchParams.has(name));
  }

  // Only an entry that is a panel can be gone back to; the page under the
  // panel (the list, Mijn profiel) is reached by closing it.
  function panelEntry(entry, origin) {
    return entry && hasPanelParam(new URL(entry.url, origin)) ? entry : null;
  }

  // The params that open a sheet on top of a panel; without them the URL is
  // that panel. Mirrors _url_drop_params in views.py.
  const CHILD_PARAMS = ["bewerken", "teamlid", "veld"];

  // The panel a directly loaded sheet sits on, or null when the URL is a
  // panel itself.
  function parentUrlOf(url) {
    const parent = new URL(url);
    CHILD_PARAMS.forEach((name) => parent.searchParams.delete(name));
    if (parent.search === url.search || !hasPanelParam(parent)) return null;
    return parent.pathname + parent.search;
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { panelEntry: panelEntry, parentUrlOf: parentUrlOf };
    return;
  }

  document.addEventListener("tabchange", (e) => {
    const bar = e.target.closest("[data-side-panel-tabs]");
    if (!bar) return;
    const selectedId = e.detail?.item?.dataset.tabPanel;
    if (!selectedId) return;
    bar.querySelectorAll("nldd-tab-bar-item").forEach((item) => {
      const panel = document.getElementById(item.dataset.tabPanel);
      if (!panel) return;
      const show = item.dataset.tabPanel === selectedId;
      panel.toggleAttribute("hidden", !show);
    });
  });

  // Everything the panel puts in the URL, stripped when it closes. The ones
  // above plus the params that only modify an open panel; 'pagina' is the
  // list's, not the panel's, so PANEL_PARAMS in views.py has one more.
  const PANEL_URL_PARAMS = PANEL_PARAMS.concat([
    "bewerken",
    "teamlid",
    "veld",
    "uitgeklapt",
  ]);

  // Entries are { url, title } of the panel being left.
  const panelStack = [];
  let _skipNextPush = false;
  let currentPanelTitle = "";
  // currentPanelTitle may only switch after the afterSettle push, or the stack
  // records the wrong title.
  let pendingNewTitle = "";

  function getSheet() {
    return document.getElementById(SHEET_ID);
  }

  function isSheetOpen(sheet) {
    if (!sheet) return false;
    // nldd-sheet exposes its open state as <dialog open> in the shadow root.
    const dlg = sheet.shadowRoot && sheet.shadowRoot.querySelector("dialog");
    return !!(dlg && dlg.open);
  }

  function openSheet() {
    const sheet = getSheet();
    if (!sheet) return;
    if (typeof sheet.show === "function") sheet.show();
    else if (typeof sheet.open === "function") sheet.open();
    document.documentElement.style.overflow = "hidden";
  }

  function closeSheet() {
    const sheet = getSheet();
    if (!sheet) return;
    if (typeof sheet.hide === "function") sheet.hide();
    else if (typeof sheet.close === "function") sheet.close();
    document.documentElement.style.overflow = "";
  }

  function clearContent() {
    const c = document.getElementById(CONTENT_ID);
    if (c) c.innerHTML = "";
  }

  // A non-empty stack is not enough: the first opening pushes the list URL, and
  // going back to the list is just closing.
  function parentPanel() {
    return panelEntry(
      panelStack[panelStack.length - 1],
      window.location.origin,
    );
  }

  // Called from afterSwap, before first paint: doing it in afterSettle redraws
  // the bar a frame later and the header visibly jumps.
  function writeBackButton(bar, section, parent) {
    // The server named the parent (data-back-url): its back-text stays, also
    // on a full page load where the stack is empty.
    if (bar.hasAttribute("data-back-url")) {
      if (section) section.removeAttribute("padding-top");
      return;
    }
    if (parent)
      bar.setAttribute(
        "back-text",
        parent.title || bar.getAttribute("back-text") || "Terug",
      );
    else bar.removeAttribute("back-text");
    if (!section) return;
    if (parent) section.removeAttribute("padding-top");
    else section.setAttribute("padding-top", "0");
  }

  // For the server-rendered first opening, where no swap happens.
  function syncPanelBackButton() {
    const content = document.getElementById(CONTENT_ID);
    if (!content) return;
    const bar = content.querySelector(":scope > nldd-top-title-bar");
    if (!bar) return;
    // A sheet loaded straight from its URL has no stack yet. Its server
    // back-text names the panel underneath, so that panel becomes the step back.
    const parentUrl = parentUrlOf(new URL(window.location));
    if (!panelStack.length && bar.hasAttribute("back-text") && parentUrl)
      panelStack.push({ url: parentUrl, title: "" });
    const parent = parentPanel();
    writeBackButton(
      bar,
      content.querySelector(":scope > nldd-simple-section"),
      parent,
    );
    currentPanelTitle = bar.getAttribute("text") || "";
  }

  function swapPanel(url) {
    if (!window.htmx) return;
    window.htmx.ajax("GET", url, {
      target: "#" + CONTENT_ID,
      swap: "innerHTML",
    });
  }

  function closeSidePanel() {
    panelStack.length = 0;
    closeSheet();
    clearContent();
    const url = new URL(window.location);
    PANEL_URL_PARAMS.forEach((name) => url.searchParams.delete(name));
    history.replaceState({}, "", url.toString());
  }

  // A sheet that names its parent (data-back-url) goes back there, so label and
  // target agree also after a save or reload left the stack behind.
  function serverBackUrl() {
    const content = document.getElementById(CONTENT_ID);
    const bar = content && content.querySelector(":scope > nldd-top-title-bar");
    return bar ? bar.getAttribute("data-back-url") : null;
  }

  function panelBack() {
    const backUrl = serverBackUrl();
    if (backUrl) {
      const backTo = panelStack.findIndex((entry) => entry.url === backUrl);
      panelStack.length = backTo === -1 ? 0 : backTo;
      history.replaceState({}, "", backUrl);
      _skipNextPush = true;
      swapPanel(backUrl);
      return;
    }
    if (panelStack.length > 0) {
      const prevUrl = panelStack.pop().url;
      const url = new URL(prevUrl, window.location.origin);
      if (hasPanelParam(url)) {
        history.replaceState({}, "", prevUrl);
        _skipNextPush = true;
        swapPanel(prevUrl);
      } else {
        closeSidePanel();
      }
    } else {
      closeSidePanel();
    }
  }

  // The panel's scroller is a div in nldd-page's shadow root, out of app.css's
  // reach; an adopted sheet, since the CSP allows no inline styles. The gutter
  // stops "Toon meer" shifting the panel sideways; the padding replaces a
  // bottom inset the component derives from a footer this sheet does not have.
  function styleScroller(page) {
    if (!page.shadowRoot || !("adoptedStyleSheets" in page.shadowRoot)) return;
    const sheet = new CSSStyleSheet();
    sheet.replaceSync(
      ".page__scroll { scrollbar-gutter: stable; padding-bottom: 24px; }",
    );
    page.shadowRoot.adoptedStyleSheets = [
      ...page.shadowRoot.adoptedStyleSheets,
      sheet,
    ];
  }

  function init() {
    // Open the sheet when the content was server-rendered (?collega=N on load).
    const content = document.getElementById(CONTENT_ID);
    if (content) {
      customElements
        .whenDefined("nldd-page")
        .then(() => content.updateComplete)
        .then(() => styleScroller(content));
    }
    if (content && content.innerHTML.trim()) {
      // This script loads before the design system, so nldd-sheet may not be
      // defined yet.
      if (getSheet()) customElements.whenDefined("nldd-sheet").then(openSheet);
      syncPanelBackButton();
    }

    document.addEventListener("select", (e) => {
      const item = e
        .composedPath()
        .find(
          (el) =>
            el instanceof Element &&
            el.dataset &&
            el.dataset.wiesAction === "team-member-delete",
        );
      if (!item) return;
      const dialog = document.getElementById("team-member-delete-dialog");
      if (!dialog) return;
      dialog.setAttribute(
        "supporting-text",
        (item.dataset.memberName || "Dit teamlid") +
          " wordt uit het team van " +
          (dialog.dataset.assignmentName || "deze opdracht") +
          " verwijderd.",
      );
      dialog.dataset.deleteUrl = item.dataset.deleteUrl || "";
      if (dialog.show) dialog.show();
    });

    document.addEventListener("click", (e) => {
      const btn = e
        .composedPath()
        .find(
          (el) =>
            el instanceof Element &&
            el.dataset &&
            (el.dataset.wiesAction === "team-member-delete-cancel" ||
              el.dataset.wiesAction === "team-member-delete-confirm"),
        );
      if (!btn) return;
      const dialog = document.getElementById("team-member-delete-dialog");
      if (!dialog) return;
      if (
        btn.dataset.wiesAction === "team-member-delete-confirm" &&
        dialog.dataset.deleteUrl &&
        window.htmx
      ) {
        window.htmx.ajax("POST", dialog.dataset.deleteUrl, {
          target: "#" + CONTENT_ID,
          swap: "innerHTML",
          headers: { "X-CSRFToken": dialog.dataset.csrf || "" },
          values: {
            terug_url: window.location.pathname + window.location.search,
          },
        });
      }
      if (dialog.hide) dialog.hide();
    });

    // Only the panel's own title bar counts; a bar in a nested overlay bubbles
    // its 'back' up too.
    document.addEventListener("back", (e) => {
      const content = document.getElementById(CONTENT_ID);
      if (!content || e.target.parentElement !== content) return;
      panelBack();
    });

    const sheet = getSheet();
    if (sheet) {
      sheet.addEventListener("close", (e) => {
        // Only the sheet's own close counts.
        if (e.target !== sheet) return;
        const url = new URL(window.location);
        if (hasPanelParam(url)) {
          panelStack.length = 0;
          clearContent();
          PANEL_URL_PARAMS.forEach((name) => url.searchParams.delete(name));
          history.replaceState({}, "", url.toString());
          document.documentElement.style.overflow = "";
        }
      });
    }

    window.addEventListener("popstate", () => {
      const url = new URL(window.location);
      const hasPanel = hasPanelParam(url);
      if (!hasPanel && isSheetOpen(getSheet())) {
        panelStack.length = 0;
        closeSheet();
        clearContent();
      } else if (hasPanel) {
        _skipNextPush = true;
        swapPanel(window.location.href);
      }
    });
  }

  // afterSwap still runs before paint (afterSettle is ~20ms later), so the back
  // button set here does not visibly jump. Bookkeeping stays in afterSettle.
  document.addEventListener("htmx:afterSwap", (event) => {
    const targetId = event.detail.target && event.detail.target.id;
    if (targetId !== CONTENT_ID) return;

    const content = document.getElementById(CONTENT_ID);
    if (!content) return;
    const bar = content.querySelector(":scope > nldd-top-title-bar");
    if (!bar) return;

    pendingNewTitle = bar.getAttribute("text") || "";

    // A server back-text names the opdracht the sheet belongs to, which is
    // only right when the user came from that panel. The stack decides, the
    // server text is the fallback title.
    const section = content.querySelector(":scope > nldd-simple-section");
    // A POST is no step in the stack: its parent is the one the GET had.
    const verb = event.detail.requestConfig && event.detail.requestConfig.verb;
    if (verb && verb.toLowerCase() !== "get") {
      if (bar.hasAttribute("back-text"))
        writeBackButton(bar, section, parentPanel());
      return;
    }

    // Under _skipNextPush the pop already happened, so panelStack[last] is the
    // parent; otherwise it is the current panel, which afterSettle will push.
    if (_skipNextPush) {
      writeBackButton(bar, section, parentPanel());
      return;
    }
    const currentPath = window.location.pathname + window.location.search;
    const requestPath =
      (event.detail.pathInfo && event.detail.pathInfo.requestPath) ||
      (event.detail.requestConfig && event.detail.requestConfig.path);
    // Landing on the URL we are already on means we returned rather than went
    // deeper, so the parent comes from the stack, not from currentPanelTitle.
    const isReturn =
      !!requestPath &&
      new URL(requestPath, window.location.origin).pathname +
        new URL(requestPath, window.location.origin).search ===
        currentPath;
    if (isReturn) {
      const backTo = panelStack.findIndex((entry) => entry.url === currentPath);
      const parentEntry = backTo > 0 ? panelStack[backTo - 1] : null;
      writeBackButton(
        bar,
        section,
        panelEntry(parentEntry, window.location.origin),
      );
      return;
    }
    const parent = panelEntry(
      { url: currentPath, title: currentPanelTitle },
      window.location.origin,
    );
    writeBackButton(bar, section, parent);
  });

  document.addEventListener("htmx:afterSettle", (event) => {
    const targetId = event.detail.target && event.detail.target.id;
    if (targetId !== CONTENT_ID) return;

    const sheet = getSheet();
    if (sheet && !isSheetOpen(sheet)) openSheet();

    if (_skipNextPush) {
      _skipNextPush = false;
      currentPanelTitle = pendingNewTitle;
      return;
    }

    // A POST sets its own URL via HX-Push-Url; pushing here would leave the
    // POST path in the address bar.
    const verb = event.detail.requestConfig && event.detail.requestConfig.verb;
    if (verb && verb.toLowerCase() !== "get") return;

    const requestPath =
      (event.detail.pathInfo && event.detail.pathInfo.requestPath) ||
      (event.detail.requestConfig && event.detail.requestConfig.path);
    if (!requestPath) return;

    const reqUrl = new URL(requestPath, window.location.origin);
    const reqPath = reqUrl.pathname + reqUrl.search;
    const currentPath = window.location.pathname + window.location.search;

    // Returning to a panel already on the stack is a step back, not deeper.
    const backTo = panelStack.findIndex((entry) => entry.url === reqPath);
    if (backTo !== -1) panelStack.length = backTo;

    if (reqPath !== currentPath) {
      // currentPanelTitle still belongs to the panel being left.
      panelStack.push({ url: currentPath, title: currentPanelTitle });
      history.pushState({}, "", reqPath);
    }
    currentPanelTitle = pendingNewTitle;
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
