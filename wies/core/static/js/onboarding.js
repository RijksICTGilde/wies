// First-login onboarding wizard: auto-open + step navigation. Skipping and
// "Aan de slag" both submit the same hidden form; the server answers with a
// `closeOnboarding` trigger.
(function () {
  "use strict";

  var wizard = document.querySelector("nldd-window[data-onboarding]");
  if (!wizard) return;

  var panels = wizard.querySelectorAll("section[data-step]");
  // Derived, since the opdracht step is conditional.
  var TOTAL_STEPS = panels.length;
  var current = 1;

  var progress = wizard.querySelector("[data-onboarding-progress]");
  var steps = progress
    ? progress.querySelectorAll("nldd-step-indicator-item")
    : [];
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

  // The edit screen takes over the window: while open there is no step.
  function showDetail(on) {
    if (!detail) return;
    detail.hidden = !on;
    if (nav) nav.hidden = on;
    if (finishWrap && on) finishWrap.hidden = true;
    if (detailNav) detailNav.hidden = !on;
    chrome.forEach(function (el) {
      el.hidden = on;
    });
    if (section) {
      if (on) section.removeAttribute("padding-top");
      else section.setAttribute("padding-top", "0");
    }
    // Anchored to the heading, so the bar collapses once it scrolls under.
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
    // Backwards only; forward goes through Volgende, which also saves.
    steps.forEach(function (step, index) {
      if (index + 1 < current) step.setAttribute("button", "");
      else step.removeAttribute("button");
    });
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

  // The inline-edit fields have no save button of their own; each form swaps
  // itself back to the read view, which the wizard does not wait for.
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

  // The bar's dismiss, not the window's `close`: nldd-window calls hide() for
  // both, so by then Overslaan and Escape are indistinguishable (#553). Bound
  // to the bar, because the window stops that dismiss propagating.
  if (titleBar) {
    titleBar.addEventListener("dismiss", complete);
  }

  wizard.addEventListener("close", function (e) {
    if (e.target !== wizard) return;
    document.documentElement.style.overflow = "";
  });

  document.body.addEventListener("htmx:afterSwap", function (e) {
    if (e.target === detail && detail.innerHTML.trim()) showDetail(true);
  });
  document.body.addEventListener("onboardingDetailClose", closeDetail);
  wizard.addEventListener("back", function () {
    if (detail && !detail.hidden) closeDetail();
    else show(current - 1);
  });

  document.body.addEventListener("closeOnboarding", function () {
    if (wizard.hide) wizard.hide();
    document.documentElement.style.overflow = "";
  });

  // show() fails silently before Lit has rendered the shadow root.
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
