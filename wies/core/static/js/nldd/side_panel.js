// NDD side panel — gebruikt nldd-sheet API (.show()/.hide()).
// Manages: panel stack voor back-navigation, URL sync, popstate.

(function () {
  "use strict";

  // --- Tab switching (Gegevens / Updates in the opdracht panel) ---
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
      panel.setAttribute("tabindex", show ? "0" : "-1");
    });
  });

  const SHEET_ID = "side-panel";
  const CONTENT_ID = "side-panel-content";
  // Queryparams die een paneel openen (spiegelt PANEL_PARAMS in views.py, minus
  // 'pagina' dat over de lijst gaat). 'bewerken' hangt aan 'plaatsing' en opent
  // dus nooit op zichzelf een paneel.
  const PANEL_PARAMS = ["collega", "opdracht", "plaatsing"];

  function hasPanelParam(url) {
    return PANEL_PARAMS.some((name) => url.searchParams.has(name));
  }

  const panelStack = [];
  let _skipNextPush = false;

  function getSheet() {
    return document.getElementById(SHEET_ID);
  }

  function isSheetOpen(sheet) {
    if (!sheet) return false;
    // nldd-sheet exposeert open state via shadow root <dialog open>
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
    PANEL_PARAMS.forEach((name) => url.searchParams.delete(name));
    url.searchParams.delete("bewerken");
    history.replaceState({}, "", url.toString());
  }

  function panelBack() {
    if (panelStack.length > 0) {
      const prevUrl = panelStack.pop();
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
    // Open sheet als content al server-side gerendered is (initial load met ?collega=N)
    const content = document.getElementById(CONTENT_ID);
    if (content && content.innerHTML.trim()) {
      // Wacht tot nldd-sheet web component klaar is
      const sheet = getSheet();
      if (sheet) {
        if (sheet.shadowRoot) {
          openSheet();
        } else {
          customElements.whenDefined("nldd-sheet").then(() => openSheet());
        }
      }
    }

    // Click delegation voor data-nldd-action knoppen (in panel content)
    document.addEventListener("click", (e) => {
      const path = e.composedPath();
      const btn = path.find(
        (el) => el instanceof Element && el.dataset && el.dataset.nddAction,
      );
      if (!btn) return;
      const action = btn.dataset.nddAction;
      // Sluiten zit niet meer hier: de panel-templates gebruiken een echte
      // nldd-top-title-bar en nldd-sheet sluit zichzelf op diens dismiss.
      if (action === "panel-back") {
        e.preventDefault();
        panelBack();
      }
    });

    // nldd-top-title-bar vuurt 'back' (bubbles + composed) als zijn terugknop
    // wordt gebruikt; child panels zoals het bewerkformulier gaan zo terug naar
    // hun ouder in de panelStack. Alleen de eigen titelbalk van het paneel telt:
    // een balk in een geneste overlay stuurt zijn eigen 'back' omhoog.
    document.addEventListener("back", (e) => {
      const content = document.getElementById(CONTENT_ID);
      if (!content || e.target.parentElement !== content) return;
      panelBack();
    });

    // nldd-sheet emit een 'close' event wanneer gebruiker op backdrop klikt of ESC drukt
    const sheet = getSheet();
    if (sheet) {
      // WORKAROUND voor een bug in het design system (@nldd/design-system 0.8.70).
      // nldd-sheet sluit zichzelf zodra er een 'dismiss' langskomt met ergens een
      // nldd-top-title-bar in het composed path — ongeacht of dat zijn EIGEN balk
      // is (zie utilities/dismiss-from-title-bar.ts, waar die beperking ook staat
      // beschreven). De datumkiezer van nldd-date-field is een popover met een
      // eigen titelbalk, en nldd-popover stopt die dismiss niet zoals sheet en
      // window dat wel doen. Gevolg: "Annuleer" in de datumkiezer sloot ook de
      // zijsheet.
      //
      // De listener hangt op de content (bubble-fase), niet op de sheet: dan is
      // het component zelf al klaar met het event — de datumkiezer sluit dus
      // gewoon — en stoppen we het net voordat de sheet het ziet. Weghalen zodra
      // de DS dit oplost.
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
        // Alleen als DEZE sheet sluit. Overlays in de inhoud (de datepicker van
        // een nldd-date-field is zelf ook een sheet) vuren een 'close' die
        // bubbelt; zonder deze check leegden we het paneel bij het sluiten
        // daarvan.
        if (e.target !== sheet) return;
        // Sync URL state als sheet via backdrop/ESC dichtgaat
        const url = new URL(window.location);
        if (hasPanelParam(url)) {
          panelStack.length = 0;
          clearContent();
          PANEL_PARAMS.forEach((name) => url.searchParams.delete(name));
          url.searchParams.delete("bewerken");
          history.replaceState({}, "", url.toString());
          document.documentElement.style.overflow = "";
        }
      });
    }

    // Browser back/forward
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

    // Alleen navigeren tussen panelen is een stap in de stack. Een POST (het
    // bewerkformulier) is dat niet: die zet zijn eigen URL via HX-Push-Url, en
    // pushen we hier alsnog, dan blijft het POST-pad in de adresbalk staan.
    const verb = event.detail.requestConfig && event.detail.requestConfig.verb;
    if (verb && verb.toLowerCase() !== "get") return;

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
