// Auto-show sheets/modals that arrive via a swap.
document.addEventListener("htmx:afterSwap", function (e) {
  // show() returns silently before Lit renders the shadow <dialog>, hence
  // updateComplete. data-auto-show is explicit because panel content also
  // carries closed dialogs, and the side panel is itself an nldd-sheet.
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
 * Gives a sheet a back button when it opens on top of another one. The template
 * cannot know this: the filter sidebar is a panel when wide and a sheet when
 * narrow, so the same button opens a child in one case only.
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
  // The narrow-screen sidebar sheet lives in a shadow root, out of reach of a
  // document query.
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
  const backText =
    (parentBar && (parentBar.getAttribute("text") || parentBar.text)) ||
    "Terug";

  const bar = sheet.querySelector("nldd-top-title-bar[slot='header']");
  if (bar) {
    if (isChild) bar.setAttribute("back-text", backText);
    else bar.removeAttribute("back-text");
  }
  const extraHeader = sheet.querySelector(
    "[slot='header']:not(nldd-top-title-bar)",
  );
  // Running text needs the space: flush against the bar a paragraph reads as a
  // continuation of the title. Forms and lists do not.
  const houdtPadding = sheet.hasAttribute("data-keep-section-padding");
  const section = sheet.querySelector("nldd-simple-section");
  if (section && !extraHeader && !houdtPadding) {
    if (isChild) section.removeAttribute("padding-top");
    else section.setAttribute("padding-top", "0");
  }
};

// Back in a child sheet means closing; the sheet underneath reappears.
document.addEventListener("back", function (e) {
  const sheet = window.wiesClosestInPath(e, "nldd-sheet");
  if (!sheet || typeof sheet.hide !== "function") return;
  // side_panel.js handles its own back: there it means a previous panel.
  if (sheet.id === "side-panel") return;
  sheet.hide();
});

// composedPath: the button may live in the dialog's shadow root.
document.addEventListener("click", function (e) {
  const btn = window.wiesClosestInPath(e, "[data-dismiss-modal]");
  if (!btn) return;
  const dialog = btn.closest("nldd-modal-dialog, nldd-sheet");
  if (dialog && typeof dialog.hide === "function") dialog.hide();
});

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
