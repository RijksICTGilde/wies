// NDD side panel on the nldd-sheet API (.show()/.hide()): panel stack for back
// navigation, URL sync and popstate.

(function () {
  "use strict";

  // nldd-tab-bar manages its own selected state and fires `tabchange`; we just
  // show the panel referenced by the selected item's data-tab-panel. Delegated
  // on document so it survives HTMX swaps of the panel content.
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
  // Query params that open a panel; mirrors PANEL_PARAMS in views.py minus
  // 'pagina', which belongs to the list. 'bewerken' only qualifies 'plaatsing'.
  const PANEL_PARAMS = ["collega", "opdracht", "plaatsing", "nieuwe-opdracht"];

  function hasPanelParam(url) {
    return PANEL_PARAMS.some((name) => url.searchParams.has(name));
  }

  // Each entry is { url, title }: the title of the panel being left, so the back
  // button can name it instead of just saying "Terug".
  const panelStack = [];
  let _skipNextPush = false;
  let currentPanelTitle = "";
  // Title of the panel that just loaded. afterSwap knows it already, but
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

  /**
   * Returns the stack entry the back button should point at, or null.
   *
   * A non-empty stack is not enough: the first panel opening pushes the list
   * URL, and going back to the list is just closing.
   */
  function parentPanel() {
    const parent = panelStack[panelStack.length - 1];
    const hasParent =
      !!parent && hasPanelParam(new URL(parent.url, window.location.origin));
    return hasParent ? parent : null;
  }

  /**
   * Writes the back button and matching padding onto the title bar and section.
   *
   * Kept separate from the computation so afterSwap can call it before the first
   * paint: setting back-text in afterSettle makes the vendor title bar redraw a
   * frame later, which shows as a jumping header.
   *
   * @param {Element} bar The panel's nldd-top-title-bar.
   * @param {?Element} section The panel's first nldd-simple-section.
   * @param {?{url: string, title: string}} parent The panel to go back to, or
   *     null for no back button.
   */
  function writeBackButton(bar, section, parent) {
    // A template that knows its own back-text (the edit form knows whose it is)
    // wins; the stack value is the fallback, "Terug" the last resort.
    if (parent)
      bar.setAttribute(
        "back-text",
        parent.title || bar.getAttribute("back-text") || "Terug",
      );
    else bar.removeAttribute("back-text");
    // With a back button the content must not sit flush against the bar.
    if (!section) return;
    if (parent) section.removeAttribute("padding-top");
    else section.setAttribute("padding-top", "0");
  }

  // For the server-rendered first panel opening (init), where no swap happens.
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
      // A shadowRoot alone is not enough: show() before the first render leaves
      // the dialog closed, so wait for updateComplete.
      const sheet = getSheet();
      if (sheet) {
        customElements
          .whenDefined("nldd-sheet")
          .then(() => sheet.updateComplete)
          .then(() => openSheet());
      }
      syncPanelBackButton();
    }

    // The row menu opens the dialog and passes name and action URL via data
    // attributes; only the destructive button in the dialog does the POST.
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

    // nldd-top-title-bar fires 'back' (bubbles + composed). Only the panel's own
    // title bar counts; a bar in a nested overlay sends its 'back' up too.
    document.addEventListener("back", (e) => {
      const content = document.getElementById(CONTENT_ID);
      if (!content || e.target.parentElement !== content) return;
      panelBack();
    });

    // nldd-sheet fires 'close' on a backdrop click or ESC.
    const sheet = getSheet();
    if (sheet) {
      // WORKAROUND for @nldd/design-system 0.8.70: nldd-sheet closes on any
      // 'dismiss' with an nldd-top-title-bar in the composed path, even a
      // foreign one (see utilities/dismiss-from-title-bar.ts). The date picker
      // of nldd-date-field is a popover with its own title bar and, unlike sheet
      // and window, nldd-popover does not stop that dismiss, so "Annuleer" in
      // the picker also closed the side sheet. The listener sits on the content
      // in the bubble phase, so the picker has already handled the event and we
      // stop it just before the sheet sees it. Remove once the DS fixes this.
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
        // Only when THIS sheet closes: overlays inside the content (the date
        // picker of an nldd-date-field is a sheet itself) bubble a 'close' too.
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

  // afterSwap runs synchronously after the DOM insert, still before paint
  // (afterSettle is ~20ms later), so the back button set here makes the first
  // paint and does not visibly jump. Stack bookkeeping stays in afterSettle.
  document.addEventListener("htmx:afterSwap", (event) => {
    const targetId = event.detail.target && event.detail.target.id;
    if (targetId !== CONTENT_ID) return;

    const content = document.getElementById(CONTENT_ID);
    if (!content) return;
    const bar = content.querySelector(":scope > nldd-top-title-bar");
    if (!bar) return;

    pendingNewTitle = bar.getAttribute("text") || "";

    // A POST (saving the edit form, removing a team member) is no step in the
    // stack and brings its own server back-text; leave a server-rendered
    // back-text alone as well.
    const verb = event.detail.requestConfig && event.detail.requestConfig.verb;
    if (verb && verb.toLowerCase() !== "get") return;
    if (bar.hasAttribute("back-text")) return;

    // The new panel's back button points at the panel being left. Under
    // _skipNextPush (back button/popstate) the pop already happened, so
    // panelStack[last] is the parent; otherwise it is the current panel, which
    // afterSettle is about to push.
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
    // deeper (the edit form after saving, where HX-Location sets the URL). The
    // parent then comes from the stack, not from currentPanelTitle, which still
    // holds the form we just finished.
    const isReturn =
      !!requestPath &&
      new URL(requestPath, window.location.origin).pathname +
        new URL(requestPath, window.location.origin).search ===
        currentPath;
    if (isReturn) {
      // The parent is the step before this one on the stack; without one we
      // came straight from the list and there is no back button.
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

    // afterSwap already wrote the visible bar; this is bookkeeping only.
    if (_skipNextPush) {
      _skipNextPush = false;
      currentPanelTitle = pendingNewTitle;
      return;
    }

    // Only navigation between panels is a step. A POST (the edit form) sets its
    // own URL via HX-Push-Url; pushing here would leave the POST path in the
    // address bar.
    const verb = event.detail.requestConfig && event.detail.requestConfig.verb;
    if (verb && verb.toLowerCase() !== "get") return;

    const requestPath =
      (event.detail.pathInfo && event.detail.pathInfo.requestPath) ||
      (event.detail.requestConfig && event.detail.requestConfig.path);
    if (!requestPath) return;

    const reqUrl = new URL(requestPath, window.location.origin);
    const reqPath = reqUrl.pathname + reqUrl.search;
    const currentPath = window.location.pathname + window.location.search;

    // Returning to a panel already on the stack is a step back, not deeper, so
    // truncate there. The edit form lands on its parent panel via HX-Location,
    // which is a GET that would otherwise leave the edit step as "previous" and
    // give a back button to the form you just finished. HX-Location sets the URL
    // itself, so reqPath equals currentPath and the block below is skipped.
    const backTo = panelStack.findIndex((entry) => entry.url === reqPath);
    if (backTo !== -1) panelStack.length = backTo;

    if (reqPath !== currentPath) {
      // currentPanelTitle still belongs to the panel being left, so it may only
      // switch to pendingNewTitle after this push.
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
