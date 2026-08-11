// TIJDELIJK — hoort thuis in het design system, niet hier.
//
// Enter in een invoerveld verstuurt het formulier (implicit submission). Dat is
// browser-standaardgedrag dat je normaal gratis krijgt, maar het werkt niet met
// nldd-text-field: de echte <input> zit in de shadow root en heeft daardoor
// `input.form === null`. De browser voert implicit submission uit vanuit die
// input, dus zonder formulier gebeurt er niets. Een verborgen submit-knop
// toevoegen helpt niet — het ontbreekt niet aan een knop maar aan de brug
// tussen input en formulier.
//
// Het veld is wél form-associated via ElementInternals (`internals.form` is
// gevuld, en de waarde gaat gewoon mee in de POST). We gebruiken die koppeling
// hier om te doen wat het component zelf zou moeten doen.
//
// Weghalen zodra nldd-text-field een eigen @keydown krijgt die
// `internals.form.requestSubmit()` aanroept: dan is dit bestand overbodig en kan
// het script uit base.html.
(function () {
  "use strict";

  // Meerregelige velden niet: daar hoort Enter een nieuwe regel te maken, net
  // als in een gewone <textarea>. Dat is precies de scheiding die de browser
  // zelf ook maakt.
  var SINGLE_LINE = "nldd-text-field";

  // Capture, want het veld stopt zijn eigen events (_handleInput doet
  // stopPropagation); in de bubble-fase zien we de keydown niet betrouwbaar.
  document.addEventListener(
    "keydown",
    function (event) {
      if (event.key !== "Enter" || event.isComposing) return;
      if (event.defaultPrevented) return;

      // composedPath omdat het doel in een shadow root ligt; event.target is
      // dan het custom element, niet de input.
      var field = event.composedPath().find(function (node) {
        return node.nodeType === 1 && node.localName === SINGLE_LINE;
      });
      if (!field) return;

      var form = field.internals && field.internals.form;
      if (!form) return;

      // requestSubmit en niet submit(): dat draait de validatie en vuurt het
      // submit-event, zodat htmx het oppikt. submit() slaat allebei over.
      event.preventDefault();
      form.requestSubmit();
    },
    true,
  );
})();
