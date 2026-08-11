// NDD side panel — gebruikt nldd-sheet API (.show()/.hide()).
// Manages: panel stack voor back-navigation, URL sync, popstate.

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
  // Queryparams die een paneel openen (spiegelt PANEL_PARAMS in views.py, minus
  // 'pagina' dat over de lijst gaat). 'bewerken' hangt aan 'plaatsing' en opent
  // dus nooit op zichzelf een paneel. 'nieuwe-opdracht' opent de aanmaak-sheet.
  const PANEL_PARAMS = ["collega", "opdracht", "plaatsing", "nieuwe-opdracht"];

  function hasPanelParam(url) {
    return PANEL_PARAMS.some((name) => url.searchParams.has(name));
  }

  // Elk item is { url, title }: de titel van het paneel dat je verlaat, zodat
  // de terugknop hem kan tonen ("Anke Jacobs" zegt meer dan "Terug").
  const panelStack = [];
  let _skipNextPush = false;
  let currentPanelTitle = "";
  // De titel van het paneel dat NET is ingeladen. afterSwap kent hem al (voor
  // de terugknop-berekening van een volgende stap), maar currentPanelTitle mag
  // pas na de afterSettle-push wisselen — anders komt de verkeerde titel op de
  // stack. afterSettle zet currentPanelTitle = pendingNewTitle als laatste.
  let pendingNewTitle = "";

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

  // Bepaalt of er een terugknop hoort bij het huidige paneel: alleen als het
  // vorige item op de stack zelf een paneel was. Niet "is de stack gevuld":
  // bij de eerste paneelopening staat de lijst-URL erop, en teruggaan naar de
  // lijst is gewoon sluiten.
  function parentPanel() {
    const parent = panelStack[panelStack.length - 1];
    const hasParent =
      !!parent && hasPanelParam(new URL(parent.url, window.location.origin));
    return hasParent ? parent : null;
  }

  // Schrijft de terugknop (back-text) en de bijbehorende padding op de balk en
  // de eerste sectie. Los van de berekening zodat afterSwap dit vóór de eerste
  // paint kan doen — zet je back-text pas in afterSettle, dan hertekent de
  // vendor-titelbalk zich een frame later en zie je de header verspringen.
  function writeBackButton(bar, section, parent) {
    // De template zet zelf al een back-text als hij die kent (het bewerkformulier
    // weet van wie het is); die niet overschrijven. Anders komt hij uit de stack,
    // en pas als beide leeg zijn wordt het "Terug".
    if (parent)
      bar.setAttribute(
        "back-text",
        parent.title || bar.getAttribute("back-text") || "Terug",
      );
    else bar.removeAttribute("back-text");
    // Staat er een terugknop, dan mag de content niet tegen de balk aan staan,
    // dus dan geen padding-top: 0 op de eerste sectie.
    if (!section) return;
    if (parent) section.removeAttribute("padding-top");
    else section.setAttribute("padding-top", "0");
  }

  // Voor de server-gerenderde eerste paneelopening (init): content staat er al,
  // dus writeBackButton schrijven na een swap is niet aan de orde.
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

  // afterSwap draait synchroon na het invoegen van de nieuwe DOM, nog vóór de
  // browser tekent (afterSettle komt ~20ms later). De terugknop hier zetten laat
  // de vendor-titelbalk hem in de éérste paint meenemen: geen zichtbare sprong.
  // De stack-boekhouding blijft in afterSettle; hier alleen de zichtbare balk.
  document.addEventListener("htmx:afterSwap", (event) => {
    const targetId = event.detail.target && event.detail.target.id;
    if (targetId !== CONTENT_ID) return;

    const content = document.getElementById(CONTENT_ID);
    if (!content) return;
    const bar = content.querySelector(":scope > nldd-top-title-bar");
    if (!bar) return;

    // De titel van het net ingeladen paneel; afterSettle zet hem straks pas op
    // currentPanelTitle (na de push, zodat de stack de juiste titel krijgt).
    pendingNewTitle = bar.getAttribute("text") || "";

    // Een POST (bewerkformulier opslaan, teamlid verwijderen) is geen stap in de
    // stack en heeft zijn eigen server-back-text; die niet met een stack-waarde
    // overschrijven. Ook een balk met een server-gerenderde back-text (bewerk-/
    // aanmaakpanelen) laten we met rust.
    const verb = event.detail.requestConfig && event.detail.requestConfig.verb;
    if (verb && verb.toLowerCase() !== "get") return;
    if (bar.hasAttribute("back-text")) return;

    // De terugknop van het NIEUWE paneel wijst naar het paneel dat we verlaten.
    // Bij _skipNextPush (terugknop/popstate) is dat pop al gebeurd, dus wijst
    // panelStack[last] naar de juiste ouder; anders is het het huidige paneel
    // (currentPath/currentPanelTitle), dat afterSettle zo meteen pusht.
    const section = content.querySelector(":scope > nldd-simple-section");
    if (_skipNextPush) {
      writeBackButton(bar, section, parentPanel());
      return;
    }
    const currentPath = window.location.pathname + window.location.search;
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

    // De zichtbare balk is al in afterSwap gezet; hier alleen de boekhouding.
    if (_skipNextPush) {
      _skipNextPush = false;
      currentPanelTitle = pendingNewTitle;
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
      // currentPanelTitle hoort nog bij het paneel dat we verlaten; pas ná de
      // push wisselen naar de titel van het nieuwe paneel (pendingNewTitle).
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
