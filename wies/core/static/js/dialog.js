// HTMX + NLDD dialog integration: auto-show sheets/modals that arrive via a swap.
document.addEventListener("htmx:afterSwap", function (e) {
  // Right after a swap the element is upgraded but Lit has not rendered, so
  // show() finds no <dialog> in the shadow root and returns silently; wait for
  // updateComplete.
  //
  // nldd-modal-dialog and nldd-sheet need an explicit data-auto-show: panel
  // content also carries closed dialogs, and the side panel is itself an
  // nldd-sheet that must not pop up on every swap.
  const selector =
    "nldd-window, nldd-modal-dialog[data-auto-show], nldd-sheet[data-auto-show]";
  e.detail.target.querySelectorAll(selector).forEach(function (dialog) {
    customElements
      .whenDefined(dialog.localName)
      .then(() => dialog.updateComplete)
      .then(() => {
        if (dialog.localName === "nldd-sheet") syncSheetBackButton(dialog);
        dialog.show();
      });
  });
});

/**
 * Gives a sheet a back button when it opens on top of another one.
 *
 * The template cannot know this up front: the filter sidebar is a panel on a
 * wide screen and a sheet on a narrow one, so the same button opens a child in
 * one case and not in the other. With a back button the content may not sit
 * flush against the bar, so the section loses its padding-top: 0.
 *
 * @param {Element} sheet The nldd-sheet that is about to open.
 */
window.syncSheetBackButton = function syncSheetBackButton(sheet) {
  function isOpen(el) {
    const dlg = el && el.shadowRoot && el.shadowRoot.querySelector("dialog");
    return !!(dlg && dlg.open);
  }

  const parentSheet = Array.from(document.querySelectorAll("nldd-sheet")).find(
    function (other) {
      return other !== sheet && isOpen(other);
    },
  );
  // On narrow screens the filter sidebar renders itself as a sheet inside its
  // own shadow root, which a document query does not reach.
  let sidebarBar = null;
  Array.from(document.querySelectorAll("nldd-sidebar-section")).forEach(
    function (section) {
      const inner =
        section.shadowRoot && section.shadowRoot.querySelector("nldd-sheet");
      if (isOpen(inner))
        sidebarBar = inner.shadowRoot.querySelector("nldd-top-title-bar");
    },
  );

  const parentBar = parentSheet
    ? parentSheet.querySelector("nldd-top-title-bar[slot='header']")
    : sidebarBar;
  const isChild = !!(parentSheet || sidebarBar);
  // Name what the back button returns to; "Terug" is the fallback for a sheet
  // underneath without a title.
  const backText =
    (parentBar && (parentBar.getAttribute("text") || parentBar.text)) ||
    "Terug";

  const bar = sheet.querySelector("nldd-top-title-bar[slot='header']");
  if (bar) {
    if (isChild) bar.setAttribute("back-text", backText);
    else bar.removeAttribute("back-text");
  }
  // Only when the bar sits directly above the section: anything else in the
  // header (a search field, say) already provides the space.
  const extraHeader = sheet.querySelector(
    "[slot='header']:not(nldd-top-title-bar)",
  );
  // A sheet opening with running text does want that space: flush against the
  // bar, a paragraph reads as a continuation of the title. Forms and lists do
  // not suffer from this, hence the exception.
  const houdtPadding = sheet.hasAttribute("data-keep-section-padding");
  const section = sheet.querySelector("nldd-simple-section");
  if (section && !extraHeader && !houdtPadding) {
    if (isChild) section.removeAttribute("padding-top");
    else section.setAttribute("padding-top", "0");
  }
};

// Back in a child sheet means closing: the sheet underneath is still open and
// reappears.
document.addEventListener("back", function (e) {
  const sheet = window.wiesClosestInPath(e, "nldd-sheet");
  if (!sheet || typeof sheet.hide !== "function") return;
  // The side panel does its own back navigation through the panelStack in
  // side_panel.js, where back means a previous panel rather than closing.
  if (sheet.id === "side-panel") return;
  sheet.hide();
});

// Delegated dismiss: [data-dismiss-modal] closes the enclosing nldd-modal-dialog
// or nldd-sheet. It replaces an inline onclick handler, which the CSP
// script-src 'self' forbids. composedPath because the button may live in the
// dialog's shadow root.
document.addEventListener("click", function (e) {
  const btn = window.wiesClosestInPath(e, "[data-dismiss-modal]");
  if (!btn) return;
  const dialog = btn.closest("nldd-modal-dialog, nldd-sheet");
  if (dialog && typeof dialog.hide === "function") dialog.hide();
});

// Server-sent closeModal trigger: close any open modal dialogs.
document.addEventListener("closeModal", function () {
  const modalContainers = [
    "labelFormModal",
    "userFormModal",
    "suborganizationFormModal",
  ];
  modalContainers.forEach((modalId) => {
    const modalContainer = document.getElementById(modalId);
    if (modalContainer) {
      const win = modalContainer.querySelector("nldd-window, nldd-sheet");
      if (win && typeof win.hide === "function") win.hide();
    }
  });
});
