// Side panel on the nldd-sheet API: panel stack for back navigation, URL sync
// and popstate.

(function () {
  "use strict";

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

  const SHEET_ID = "side-panel";
  const CONTENT_ID = "side-panel-content";
  // Mirrors PANEL_PARAMS in views.py minus 'pagina', which belongs to the list.
  const PANEL_PARAMS = ["collega", "opdracht", "plaatsing", "nieuwe-opdracht"];

  function hasPanelParam(url) {
    return PANEL_PARAMS.some((name) => url.searchParams.has(name));
  }

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
    const parent = panelStack[panelStack.length - 1];
    const hasParent =
      !!parent && hasPanelParam(new URL(parent.url, window.location.origin));
    return hasParent ? parent : null;
  }

  // Called from afterSwap, before first paint: doing it in afterSettle redraws
  // the bar a frame later and the header visibly jumps.
  function writeBackButton(bar, section, parent) {
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
    PANEL_PARAMS.forEach((name) => url.searchParams.delete(name));
    url.searchParams.delete("bewerken");
    history.replaceState({}, "", url.toString());
  }

  function panelBack() {
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

  function init() {
    // Open the sheet when the content was server-rendered (?collega=N on load).
    const content = document.getElementById(CONTENT_ID);
    if (content && content.innerHTML.trim()) {
      // show() before the first render leaves the dialog closed.
      const sheet = getSheet();
      if (sheet) {
        customElements
          .whenDefined("nldd-sheet")
          .then(() => sheet.updateComplete)
          .then(() => openSheet());
      }
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
      // WORKAROUND @nldd/design-system 0.8.70: nldd-sheet closes on any
      // 'dismiss' carrying a foreign nldd-top-title-bar in its composed path,
      // so "Annuleer" in a date picker also closed the panel. Bubble-phase, so
      // the picker has handled it first. Remove once the DS fixes this.
      const content = document.getElementById(CONTENT_ID);
      if (content) {
        content.addEventListener("dismiss", (e) => {
          const ownBar = content.querySelector(":scope > nldd-top-title-bar");
          const bar = e
            .composedPath()
            .find(
              (el) =>
                el instanceof Element &&
                el.tagName.toLowerCase() === "nldd-top-title-bar",
            );
          if (bar && bar !== ownBar) e.stopPropagation();
        });
      }

      sheet.addEventListener("close", (e) => {
        // Overlays inside the content (a date picker is a sheet itself) bubble
        // a 'close' too.
        if (e.target !== sheet) return;
        const url = new URL(window.location);
        if (hasPanelParam(url)) {
          panelStack.length = 0;
          clearContent();
          PANEL_PARAMS.forEach((name) => url.searchParams.delete(name));
          url.searchParams.delete("bewerken");
          url.searchParams.delete("teamlid");
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

    // A POST is no step in the stack and brings its own server back-text.
    const verb = event.detail.requestConfig && event.detail.requestConfig.verb;
    if (verb && verb.toLowerCase() !== "get") return;
    if (bar.hasAttribute("back-text")) return;

    // Under _skipNextPush the pop already happened, so panelStack[last] is the
    // parent; otherwise it is the current panel, which afterSettle will push.
    const section = content.querySelector(":scope > nldd-simple-section");
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
        parentEntry &&
          hasPanelParam(new URL(parentEntry.url, window.location.origin))
          ? parentEntry
          : null,
      );
      return;
    }
    const parent = hasPanelParam(new URL(currentPath, window.location.origin))
      ? { url: currentPath, title: currentPanelTitle }
      : null;
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
