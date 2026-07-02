// First-login onboarding wizard: auto-open + step navigation.
// The dialog is rendered inline by base.html (not via HTMX), so we open it
// ourselves on load. Skip/finish POST to onboarding-complete via HTMX; the
// server replies with an `closeOnboarding` trigger which closes the dialog.
(function () {
  "use strict";

  var dialog = document.querySelector("dialog[data-onboarding]");
  if (!dialog) return;

  var panels = dialog.querySelectorAll(".onboarding-panel");
  // Step count is derived, not fixed: the "Controleer je opdracht" step only
  // renders when the consultant is placed on an assignment, so the total is 5
  // or 6 depending on the template. One progress dot is rendered per panel.
  var TOTAL_STEPS = panels.length;
  var current = 1;

  var dots = dialog.querySelectorAll(".onboarding-step-dot");
  var backBtn = dialog.querySelector("[data-onboarding-back]");
  var nextBtn = dialog.querySelector("[data-onboarding-next]");
  var finishForm = dialog.querySelector(".onboarding-finish-form");

  function show(step) {
    current = Math.min(Math.max(step, 1), TOTAL_STEPS);
    panels.forEach(function (panel) {
      var isCurrent = Number(panel.getAttribute("data-step")) === current;
      panel.hidden = !isCurrent;
      panel.classList.toggle("is-active", isCurrent);
    });
    dots.forEach(function (dot) {
      var dotStep = Number(dot.getAttribute("data-dot"));
      dot.classList.toggle("is-active", dotStep === current);
      dot.classList.toggle("is-done", dotStep < current);
    });
    // Back button hidden on first step.
    if (backBtn) backBtn.hidden = current === 1;
    // Last step swaps the Next button for the finish form.
    var onLast = current === TOTAL_STEPS;
    if (nextBtn) nextBtn.hidden = onLast;
    if (finishForm) finishForm.hidden = !onLast;
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", function () {
      show(current + 1);
    });
  }
  if (backBtn) {
    backBtn.addEventListener("click", function () {
      show(current - 1);
    });
  }

  // Rijksprofiel "Koppelen" — backend link not built yet; reveal a notice.
  var rijksprofielBtn = dialog.querySelector("[data-rijksprofiel-koppelen]");
  var rijksprofielNotice = dialog.querySelector("[data-rijksprofiel-notice]");
  if (rijksprofielBtn && rijksprofielNotice) {
    rijksprofielBtn.addEventListener("click", function () {
      rijksprofielNotice.hidden = false;
    });
  }

  // Server confirms completion (skip or finish) → close in place.
  document.body.addEventListener("closeOnboarding", function () {
    dialog.close();
    document.documentElement.style.overflow = "";
  });

  dialog.addEventListener("close", function () {
    document.documentElement.style.overflow = "";
  });

  // Open on load. showModal() is a no-op if the dialog is already open.
  if (!dialog.open) {
    show(1);
    dialog.showModal();
    document.documentElement.style.overflow = "hidden";
  }
})();
