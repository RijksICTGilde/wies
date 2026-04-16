// NDD side panel — gebruikt ndd-sheet API (.show()/.hide()).
// Manages: panel stack voor back-navigation, URL sync, popstate.

(function () {
  "use strict";

  const SHEET_ID = "ndd-side-panel";
  const CONTENT_ID = "ndd-side-panel-content";

  const panelStack = [];
  let _skipNextPush = false;

  function getSheet() {
    return document.getElementById(SHEET_ID);
  }

  function isSheetOpen(sheet) {
    if (!sheet) return false;
    // ndd-sheet exposeert open state via shadow root <dialog open>
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
    url.searchParams.delete("collega");
    url.searchParams.delete("opdracht");
    history.replaceState({}, "", url.toString());
  }

  function panelBack() {
    if (panelStack.length > 0) {
      const prevUrl = panelStack.pop();
      const url = new URL(prevUrl, window.location.origin);
      if (url.searchParams.has("collega") || url.searchParams.has("opdracht")) {
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
    // Open sheet als content al server-side gerendered is (initial load met ?collega=N)
    const content = document.getElementById(CONTENT_ID);
    if (content && content.innerHTML.trim()) {
      // Wacht tot ndd-sheet web component klaar is
      const sheet = getSheet();
      if (sheet) {
        if (sheet.shadowRoot) {
          openSheet();
        } else {
          customElements.whenDefined("ndd-sheet").then(() => openSheet());
        }
      }
    }

    // Click delegation voor data-ndd-action knoppen (in panel content)
    document.addEventListener("click", (e) => {
      const path = e.composedPath();
      const btn = path.find(
        (el) => el instanceof Element && el.dataset && el.dataset.nddAction,
      );
      if (!btn) return;
      const action = btn.dataset.nddAction;
      if (action === "panel-back") {
        e.preventDefault();
        panelBack();
      } else if (action === "panel-close") {
        e.preventDefault();
        closeSidePanel();
      }
    });

    // ndd-sheet emit een 'close' event wanneer gebruiker op backdrop klikt of ESC drukt
    const sheet = getSheet();
    if (sheet) {
      sheet.addEventListener("close", () => {
        // Sync URL state als sheet via backdrop/ESC dichtgaat
        const url = new URL(window.location);
        if (
          url.searchParams.has("collega") ||
          url.searchParams.has("opdracht")
        ) {
          panelStack.length = 0;
          clearContent();
          url.searchParams.delete("collega");
          url.searchParams.delete("opdracht");
          history.replaceState({}, "", url.toString());
          document.documentElement.style.overflow = "";
        }
      });
    }

    // Browser back/forward
    window.addEventListener("popstate", () => {
      const url = new URL(window.location);
      const hasPanel =
        url.searchParams.has("collega") || url.searchParams.has("opdracht");
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

  // Na HTMX swap in panel content: open sheet + push history
  document.addEventListener("htmx:afterSettle", (event) => {
    const targetId = event.detail.target && event.detail.target.id;
    if (targetId !== CONTENT_ID) return;

    // Open sheet als hij nog niet open is
    const sheet = getSheet();
    if (sheet && !isSheetOpen(sheet)) openSheet();

    if (_skipNextPush) {
      _skipNextPush = false;
      return;
    }

    const requestPath =
      (event.detail.pathInfo && event.detail.pathInfo.requestPath) ||
      (event.detail.requestConfig && event.detail.requestConfig.path);
    if (!requestPath) return;

    const reqUrl = new URL(requestPath, window.location.origin);
    const reqPath = reqUrl.pathname + reqUrl.search;
    const currentPath = window.location.pathname + window.location.search;
    if (reqPath !== currentPath) {
      panelStack.push(currentPath);
      history.pushState({}, "", reqPath);
    }
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
