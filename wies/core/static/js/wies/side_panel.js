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

  // Elk item is { url, title }: de titel van het paneel dat je verlaat, zodat
  // de terugknop hem kan tonen ("Anke Jacobs" zegt meer dan "Terug").
  const panelStack = [];
  let _skipNextPush = false;
  let currentPanelTitle = "";

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

  // De terugknop hoort bij de vraag "waar kwam je vandaan": alleen als er een
  // vorig paneel in de stack staat. Staat hij er, dan mag de content niet tegen
  // de balk aan staan, dus dan geen padding-top: 0 op de eerste sectie.
  function syncPanelBackButton() {
    const content = document.getElementById(CONTENT_ID);
    if (!content) return;
    const bar = content.querySelector(":scope > nldd-top-title-bar");
    if (!bar) return;
    // Niet "is de stack gevuld": bij de eerste paneelopening staat de lijst-URL
    // erop, en teruggaan naar de lijst is gewoon sluiten. Een terugknop hoort er
    // alleen als het vorige item zelf een paneel was.
    const parent = panelStack[panelStack.length - 1];
    const hasParent =
      !!parent && hasPanelParam(new URL(parent.url, window.location.origin));
    // Kan het, dan wijst de knop terug met een naam. De template zet er zelf al
    // een als hij die kent (het bewerkformulier weet van wie het is); anders
    // komt hij uit de stack, en pas als beide leeg zijn wordt het "Terug".
    if (hasParent)
      bar.setAttribute(
        "back-text",
        parent.title || bar.getAttribute("back-text") || "Terug",
      );
    else bar.removeAttribute("back-text");
    currentPanelTitle = bar.getAttribute("text") || "";
    const section = content.querySelector(":scope > nldd-simple-section");
    if (!section) return;
    if (hasParent) section.removeAttribute("padding-top");
    else section.setAttribute("padding-top", "0");
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
    // Open sheet als content al server-side gerendered is (initial load met ?collega=N)
    const content = document.getElementById(CONTENT_ID);
    if (content && content.innerHTML.trim()) {
      // Wacht tot nldd-sheet klaar is: alleen een shadowRoot is niet genoeg,
      // show() vlak voor de eerste render laat de dialog dicht.
      const sheet = getSheet();
      if (sheet) {
        customElements
          .whenDefined("nldd-sheet")
          .then(() => sheet.updateComplete)
          .then(() => openSheet());
      }
      syncPanelBackButton();
    }

    // Click delegation voor data-wies-action knoppen (in panel content)
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

    // --- Teamlid verwijderen: bevestigingsdialoog -----------------------
    // Het rijmenu opent de dialoog en geeft naam + actie-URL mee via data-
    // attributen; pas de destructieve knop in de dialoog voert de POST uit.
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
          url.searchParams.delete("teamlid");
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
      syncPanelBackButton();
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
      // currentPanelTitle hoort nog bij het paneel dat we verlaten: de sync
      // voor de nieuwe inhoud draait pas hieronder.
      panelStack.push({ url: currentPath, title: currentPanelTitle });
      history.pushState({}, "", reqPath);
    }
    syncPanelBackButton();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
