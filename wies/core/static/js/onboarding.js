// First-login onboarding wizard: auto-open + step navigation.
// The window is inline in base.html rather than swapped in, so it is opened
// here. Skipping (the title bar dismiss) and "Aan de slag" both submit the same
// hidden form; the server answers with a `closeOnboarding` trigger. Escape only
// closes for now — the wizard returns on the next page.
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
  // The short step names from the indicator; the heading in the body may be
  // longer.
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

  /**
   * Shows or hides the assignment edit screen, which takes over the window.
   *
   * While it is open there is no current step, so the panels, the step
   * navigation and the step indicator go away and the title bar gets a back
   * button.
   *
   * @param {boolean} on True to show the edit screen; false to return to the
   *     steps.
   */
  function showDetail(on) {
    if (!detail) return;
    detail.hidden = !on;
    if (nav) nav.hidden = on;
    if (finishWrap && on) finishWrap.hidden = true;
    if (detailNav) detailNav.hidden = !on;
    chrome.forEach(function (el) {
      el.hidden = on;
    });
    // Without the step indicator on top the section keeps its normal padding;
    // in a step it sits flush against the indicator.
    if (section) {
      if (on) section.removeAttribute("padding-top");
      else section.setAttribute("padding-top", "0");
    }
    // In the edit screen the bar carries the assignment name, anchored to the
    // heading so it collapses to icon plus name once that scrolls under it.
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

  /**
   * Shows the given wizard step and updates the indicator, title bar and nav.
   *
   * @param {number} step The 1-based step number; clamped to the range.
   */
  function show(step) {
    current = Math.min(Math.max(step, 1), TOTAL_STEPS);
    panels.forEach(function (panel) {
      panel.hidden = Number(panel.getAttribute("data-step")) !== current;
    });
    if (progress) progress.setAttribute("current", String(current));
    // Backwards only: a completed step is a button, an upcoming one is not.
    // Forward goes through Volgende, which also saves the step.
    steps.forEach(function (step, index) {
      if (index + 1 < current) step.setAttribute("button", "");
      else step.removeAttribute("button");
    });
    // The button says "Terug" rather than the previous step's name, which the
    // indicator already shows. The bar anchors to the heading so it collapses
    // to back button plus name when that scrolls away.
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
    // On the last step "Aan de slag" takes the place of "Volgende".
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

  /**
   * Submits the inline-edit forms of a step when leaving it.
   *
   * The fields open directly (inline_edit_form) without a save button of their
   * own. Each form posts to its own endpoint and swaps itself back to the read
   * view, which the wizard does not wait for.
   *
   * @param {number} step The 1-based step number whose forms are submitted.
   */
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
  // The step itself is the button; its click bubbles up to the indicator.
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

  // Only Overslaan completes the onboarding; Escape closes for now (#553).
  // Hence the title bar's dismiss and not the window's `close`: nldd-window
  // calls hide() for both, so by then they are indistinguishable. The listener
  // sits on the bar itself because the window stops that dismiss propagating.
  if (titleBar) {
    titleBar.addEventListener("dismiss", complete);
  }

  wizard.addEventListener("close", function (e) {
    if (e.target !== wizard) return;
    document.documentElement.style.overflow = "";
  });

  // The edit screen was swapped in, so show it. Its back button and a
  // successful save (HX-Trigger from the view) return to the step.
  document.body.addEventListener("htmx:afterSwap", function (e) {
    if (e.target === detail && detail.innerHTML.trim()) showDetail(true);
  });
  document.body.addEventListener("onboardingDetailClose", closeDetail);
  wizard.addEventListener("back", function () {
    if (detail && !detail.hidden) closeDetail();
    else show(current - 1);
  });

  // Server confirms completion (skip or finish) → close in place.
  document.body.addEventListener("closeOnboarding", function () {
    if (wizard.hide) wizard.hide();
    document.documentElement.style.overflow = "";
  });

  // show() fails silently before Lit has rendered the shadow root, so wait for
  // updateComplete.
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
