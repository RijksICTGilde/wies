// First-login onboarding wizard: auto-open + step navigation.
// Het venster staat inline in base.html (niet via HTMX), dus we openen het hier
// zelf. Overslaan (de dismiss van de title bar) en "Aan de slag" dienen beide
// hetzelfde verborgen formulier in; de server antwoordt met een
// `closeOnboarding`-trigger, waarop we het venster sluiten. Escape sluit het
// venster alleen voor nu: de wizard komt bij de volgende pagina terug.
(function () {
  "use strict";

  var wizard = document.querySelector("nldd-window[data-onboarding]");
  if (!wizard) return;

  var panels = wizard.querySelectorAll("section[data-step]");
  // Derived from the rendered panels, since the opdracht step is conditional.
  var TOTAL_STEPS = panels.length;
  var current = 1;

  var progress = wizard.querySelector("[data-onboarding-progress]");
  var steps = progress
    ? progress.querySelectorAll("nldd-step-indicator-item")
    : [];
  // De korte stapnamen uit de indicator; de kop in de tekst mag langer zijn.
  var stepTitles = Array.prototype.map.call(steps, function (step) {
    return step.getAttribute("text") || "";
  });
  var nextBtn = wizard.querySelector("[data-onboarding-next]");
  var finishBtn = wizard.querySelector("[data-onboarding-finish]");
  var finishWrap = wizard.querySelector("[data-onboarding-finish-wrap]");
  var completeForm = document.getElementById("onboardingCompleteForm");
  var nav = wizard.querySelector("[data-onboarding-nav]");
  var titleBar = wizard.querySelector("nldd-top-title-bar");
  var titleBarText = titleBar ? titleBar.getAttribute("text") : "";
  var detail = document.getElementById("onboarding-detail");
  var detailNav = wizard.querySelector("[data-onboarding-detail-nav]");
  var section = wizard.querySelector("[data-onboarding-section]");
  var detailSave = wizard.querySelector("[data-onboarding-detail-save]");
  var chrome = wizard.querySelectorAll("[data-onboarding-chrome]");
  var completing = false;

  // Het bewerkscherm van een opdracht neemt het venster over: de stappen, de
  // stapnavigatie en de stapindicator gaan weg zolang het openstaat (je bent
  // dan niet in een stap), en de titelbalk krijgt de terugknop.
  function showDetail(on) {
    if (!detail) return;
    detail.hidden = !on;
    if (nav) nav.hidden = on;
    if (finishWrap && on) finishWrap.hidden = true;
    if (detailNav) detailNav.hidden = !on;
    chrome.forEach(function (el) {
      el.hidden = on;
    });
    // Zonder stapindicator bovenaan hoort de sectie zijn gewone padding te
    // hebben; in de stappen begint hij strak tegen de indicator (padding-top 0).
    if (section) {
      if (on) section.removeAttribute("padding-top");
      else section.setAttribute("padding-top", "0");
    }
    // In het bewerkscherm draagt de balk de opdrachtnaam, verankerd aan de titel
    // in de inhoud: bovenaan zie je de terugknop met tekst, en zodra de titel
    // onder de balk door scrolt klapt hij samen tot icoonknop plus naam.
    if (titleBar && on) {
      var detailHeading = detail.querySelector("[data-detail-title]");
      titleBar.setAttribute("back-text", "Terug");
      titleBar.setAttribute(
        "text",
        detailHeading ? detailHeading.textContent.trim() : titleBarText,
      );
      if (detailHeading && detailHeading.id)
        titleBar.setAttribute("collapse-anchor", detailHeading.id);
    }
    if (on)
      panels.forEach(function (panel) {
        panel.hidden = true;
      });
    else show(current);
  }

  function closeDetail() {
    if (detail) detail.innerHTML = "";
    showDetail(false);
  }

  function show(step) {
    current = Math.min(Math.max(step, 1), TOTAL_STEPS);
    panels.forEach(function (panel) {
      panel.hidden = Number(panel.getAttribute("data-step")) !== current;
    });
    if (progress) progress.setAttribute("current", String(current));
    // Alleen terug: een afgeronde stap is een knop, de stappen die nog komen
    // niet. Vooruit ga je met Volgende, dat de stap ook opslaat.
    steps.forEach(function (step, index) {
      if (index + 1 < current) step.setAttribute("button", "");
      else step.removeAttribute("button");
    });
    // De knop zegt "Terug" en niet de naam van de vorige stap: die staat al in
    // de stapindicator. De balk verankert aan de kop in de tekst, zodat hij bij
    // wegscrollen samenklapt tot terugknop plus naam.
    if (titleBar) {
      var heading = wizard.querySelector(
        'section[data-step="' + current + '"] [data-step-title]',
      );
      if (current === 1) {
        titleBar.removeAttribute("back-text");
        titleBar.removeAttribute("collapse-anchor");
        titleBar.setAttribute("text", titleBarText);
      } else {
        titleBar.setAttribute("back-text", "Terug");
        titleBar.setAttribute("text", stepTitles[current - 1] || "");
        if (heading && heading.id)
          titleBar.setAttribute("collapse-anchor", heading.id);
        else titleBar.removeAttribute("collapse-anchor");
      }
    }
    // Op de laatste stap staat "Aan de slag" waar anders "Volgende" staat:
    // onder de inhoud van de stap die je net hebt gelezen.
    var onLast = current === TOTAL_STEPS;
    if (nav) nav.hidden = onLast;
    if (finishWrap) finishWrap.hidden = !onLast;
  }

  function complete() {
    if (completing || !completeForm) return;
    completing = true;
    if (window.htmx) window.htmx.trigger(completeForm, "submit");
    else completeForm.submit();
  }

  // De labelvelden staan direct open (inline_edit_form), zonder eigen
  // opslaanknop: bij het verlaten van een stap dienen we de formulieren van die
  // stap in. Elk formulier post naar zijn eigen inline-edit-endpoint en swapt
  // zichzelf naar de leesweergave; de wizard hoeft daar niet op te wachten.
  function saveStep(step) {
    if (!window.htmx) return;
    panels.forEach(function (panel) {
      if (Number(panel.getAttribute("data-step")) !== step) return;
      panel
        .querySelectorAll("[data-inline-edit-form]")
        .forEach(function (form) {
          window.htmx.trigger(form, "submit");
        });
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", function () {
      saveStep(current);
      show(current + 1);
    });
  }
  // De stap zelf is de knop; de klik borrelt op naar de indicator.
  if (progress) {
    progress.addEventListener("click", function (e) {
      var item = e.target.closest("nldd-step-indicator-item");
      if (!item || !item.hasAttribute("button")) return;
      var index = Array.prototype.indexOf.call(steps, item);
      if (index >= 0) show(index + 1);
    });
  }
  if (detailSave) {
    detailSave.addEventListener("click", function () {
      var form =
        detail && detail.querySelector("[data-onboarding-detail-form]");
      if (form && window.htmx) window.htmx.trigger(form, "submit");
    });
  }
  if (finishBtn) {
    finishBtn.addEventListener("click", function () {
      saveStep(current);
      complete();
    });
  }

  // Alleen Overslaan vinkt de onboarding af; Escape sluit het venster voor nu
  // (#553). Vandaar de dismiss van de titelbalk en niet de `close` van het
  // venster: nldd-window roept op allebei hide() aan, dus in die `close` zijn ze
  // niet meer te onderscheiden. De listener zit op de titelbalk zelf, want het
  // venster stopt de propagatie van zo'n dismiss.
  if (titleBar) {
    titleBar.addEventListener("dismiss", complete);
  }

  wizard.addEventListener("close", function (e) {
    if (e.target !== wizard) return;
    document.documentElement.style.overflow = "";
  });

  // Het bewerkscherm is binnengeswapt → tonen. De terugknop erin en een
  // geslaagde opslag (HX-Trigger uit de view) brengen je terug naar de stap.
  document.body.addEventListener("htmx:afterSwap", function (e) {
    if (e.target === detail && detail.innerHTML.trim()) showDetail(true);
  });
  document.body.addEventListener("onboardingDetailClose", closeDetail);
  // De terugknop van de titelbalk: alleen relevant terwijl het bewerkscherm
  // openstaat, want anders staat hij er niet.
  wizard.addEventListener("back", function () {
    if (detail && !detail.hidden) closeDetail();
    else show(current - 1);
  });

  // Server confirms completion (skip or finish) → close in place.
  document.body.addEventListener("closeOnboarding", function () {
    if (wizard.hide) wizard.hide();
    document.documentElement.style.overflow = "";
  });

  customElements
    .whenDefined("nldd-window")
    .then(function () {
      return wizard.updateComplete;
    })
    .then(function () {
      show(1);
      if (wizard.show) wizard.show();
      document.documentElement.style.overflow = "hidden";
    });
})();
