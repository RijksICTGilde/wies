// HTMX + NLDD dialog integration: auto-show sheets/modals that arrive via a swap.
document.addEventListener("htmx:afterSwap", function (e) {
  // show() reads the <dialog> out of the shadow root and returns silently when
  // it isn't there yet. Right after a swap the element is upgraded but Lit has
  // not rendered, so wait for updateComplete or the modal stays invisible.
  //
  // nldd-modal-dialog and nldd-sheet only open with an explicit
  // data-auto-show: panel content carries closed dialogs too (the team-member
  // confirm), and the side panel itself is an nldd-sheet that must not pop up
  // on every swap.
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

/** Staat er al een sheet open? Dan is de sheet die nu opent een child en hoort
 *  hij een terugknop te hebben; opent hij rechtstreeks vanaf de pagina, dan
 *  niet. Dat is niet vooraf te weten in de template: de filterzijbalk is een
 *  paneel op een breed scherm en een sheet op een smal, dus dezelfde knop opent
 *  de ene keer een child en de andere keer niet.
 *
 *  Met een terugknop mag de content niet tegen de balk aan staan: dan gaat de
 *  padding-top: 0 van de eerste sectie eraf. */
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
  // De filterzijbalk toont zichzelf op smalle schermen als sheet in zijn eigen
  // shadow root, dus die vind je niet met een document-query.
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
  // De terugknop wijst terug naar iets met een naam; die naam zegt meer dan
  // "Terug". Alleen als de sheet eronder geen titel heeft valt het terug op het
  // generieke woord.
  const backText =
    (parentBar && (parentBar.getAttribute("text") || parentBar.text)) ||
    "Terug";

  const bar = sheet.querySelector("nldd-top-title-bar[slot='header']");
  if (bar) {
    if (isChild) bar.setAttribute("back-text", backText);
    else bar.removeAttribute("back-text");
  }
  // Alleen wanneer de balk direct boven de sectie staat. Zit er nog iets anders
  // in de header (een zoekveld bijvoorbeeld), dan levert dat de ruimte al en
  // houdt de sectie zijn eigen padding.
  const extraHeader = sheet.querySelector(
    "[slot='header']:not(nldd-top-title-bar)",
  );
  // Een sheet die met lopende tekst opent wil die ruimte juist wel: strak tegen
  // de balk leest een alinea als een voortzetting van de titel. Formulieren en
  // lijsten hebben er geen last van, vandaar dat dit de uitzondering is.
  const houdtPadding = sheet.hasAttribute("data-keep-section-padding");
  const section = sheet.querySelector("nldd-simple-section");
  if (section && !extraHeader && !houdtPadding) {
    if (isChild) section.removeAttribute("padding-top");
    else section.setAttribute("padding-top", "0");
  }
};

// Terug in een child-sheet betekent hetzelfde als sluiten — de sheet eronder
// staat nog open en komt weer tevoorschijn.
document.addEventListener("back", function (e) {
  const sheet = e.composedPath().find(function (el) {
    return el.localName === "nldd-sheet";
  });
  if (!sheet || typeof sheet.hide !== "function") return;
  // Het zijpaneel doet zijn eigen terug-navigatie (side_panel.js loopt door de
  // panelStack); daar betekent terug een vorig paneel, niet sluiten.
  if (sheet.id === "side-panel") return;
  sheet.hide();
});

// Delegated dismiss: een knop met [data-dismiss-modal] sluit de omvattende
// nldd-modal-dialog of nldd-sheet. Vervangt een inline onclick-handler, zodat
// de CSP script-src 'self' kan blijven (geen 'unsafe-inline'). composedPath
// omdat de knop in de shadow root van het dialog kan zitten.
document.addEventListener("click", function (e) {
  const btn = e
    .composedPath()
    .find(
      (el) =>
        el instanceof Element &&
        el.matches &&
        el.matches("[data-dismiss-modal]"),
    );
  if (!btn) return;
  const dialog = btn.closest("nldd-modal-dialog, nldd-sheet");
  if (dialog && typeof dialog.hide === "function") dialog.hide();
});

// Listen for closeModal trigger from server
document.addEventListener("closeModal", function () {
  // Close any open modal dialogs
  const modalContainers = [
    "labelFormModal",
    "userFormModal",
    "suborganizationFormModal",
    "clientModalContainer",
    "errorSheet",
  ];
  modalContainers.forEach((modalId) => {
    const modalContainer = document.getElementById(modalId);
    if (modalContainer) {
      const win = modalContainer.querySelector("nldd-window, nldd-sheet");
      if (win && typeof win.hide === "function") win.hide();
    }
  });
});
