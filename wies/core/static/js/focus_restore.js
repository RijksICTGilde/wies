// Geeft de focus een bestemming als een htmx-swap hem laat vallen.
//
// Vervangt een swap het element waar de focus op stond, dan komt de focus op
// <body> terecht en begint de volgende Tab weer bovenaan de pagina. Vooral
// hinderlijk bij toetsenbord- en schermlezergebruik.
//
// htmx herstelt focus zelf, maar alleen als er na de swap een element met
// hetzelfde id bestaat. Dat dekt een formulier dat opnieuw rendert, niet een
// formulier dat door een leesweergave vervangen wordt.
//
// De regel is generiek, dus geen markup per knop of per formulier:
//
//   0. Alleen ingrijpen als de focus echt naar <body> is gevallen. Bleef hij
//      ergens staan (zoeken en filteren verversen de lijst terwijl je in het
//      zoekveld staat), dan is er niets aan de hand en blijven we eraf.
//   1. Zette de server [autofocus] in de nieuwe inhoud, dan heeft htmx die al
//      gefocust en weet de server het beter dan wij.
//   2. Terug naar het meest recente element dat een swap veroorzaakte en dat we
//      in de huidige inhoud kunnen terugvinden.
//   3. Anders naar de vervangen container zelf, zodat je bovenaan de nieuwe
//      inhoud staat in plaats van bovenaan de pagina.
//
// Waarom stap 2 een stapel is en niet één element: een opslag die met
// HX-Location terugspringt levert drie swaps op. Je drukt "Periode wijzigen"
// (swap 1), je dient het formulier in (swap 2), en htmx haalt daarna zelf het
// paneel opnieuw op (swap 3). Die laatste heeft geen bronelement -- htmx roept
// intern `ajax("get", ...)` aan, dus `requestConfig.elt` is `document.body`.
// De knop waar je vandaan kwam zit dan twee stappen terug.
//
// Niet conditioneel op muis versus toetsenbord: :focus-visible regelt al dat een
// muisgebruiker geen ring ziet, en een schermlezergebruiker bedient vaak juist
// wel met de muis.
(function () {
  "use strict";

  // Op volgorde van betrouwbaarheid. Een id is uniek; een URL identificeert de
  // actie, wat voor deze panelen net zo goed werkt en niets van de templates
  // vraagt. Een verwijzing naar de node zelf is waardeloos: die is na een
  // opnieuw opgehaald paneel losgekoppeld.
  const IDENTIFYING_ATTRIBUTES = ["id", "hx-get", "hx-post", "href"];

  const MAX_DEPTH = 5;

  // Nieuwste eerst. Elk item beschrijft een element in plaats van ernaar te
  // wijzen, zodat het een verse render overleeft.
  let trail = [];

  function describe(element) {
    if (!element || typeof element.getAttribute !== "function") return null;
    for (const attribute of IDENTIFYING_ATTRIBUTES) {
      const value = element.getAttribute(attribute);
      if (value) return { attribute, value };
    }
    return null;
  }

  function isVisible(element) {
    return typeof element.checkVisibility === "function"
      ? element.checkVisibility()
      : true;
  }

  // De zichtbare kandidaat wint: een actie staat vaak twee keer in de DOM, als
  // knop en als verborgen item in het overflowmenu ernaast.
  function resolve(descriptor) {
    const candidates = [
      ...document.querySelectorAll(`[${descriptor.attribute}]`),
    ].filter(
      (candidate) =>
        candidate.getAttribute(descriptor.attribute) === descriptor.value,
    );
    return candidates.find(isVisible) || null;
  }

  // focus() op een custom element zonder delegatesFocus doet niets en meldt dat
  // niet, dus controleren of het pakte in plaats van aannemen.
  function focusTook(element) {
    return (
      document.activeElement === element ||
      element.contains(document.activeElement)
    );
  }

  function focusFromTrail() {
    for (let index = 0; index < trail.length; index++) {
      const element = resolve(trail[index]);
      if (!element || typeof element.focus !== "function") continue;
      element.focus();
      if (!focusTook(element)) continue;
      // Alles tot en met deze stap is afgehandeld; wat nieuwer was hoort bij een
      // niveau waar we net vandaan komen.
      trail = trail.slice(index + 1);
      return true;
    }
    return false;
  }

  document.addEventListener("htmx:beforeRequest", (event) => {
    const descriptor = describe(event.detail.elt);
    if (descriptor) trail = [descriptor, ...trail].slice(0, MAX_DEPTH);
  });

  // Een terugsprong in de browsergeschiedenis is een andere context; wat we
  // onthouden hadden gaat daar niet over.
  document.addEventListener("htmx:historyRestore", () => {
    trail = [];
  });

  // Bewust geen "wis de stapel als de gebruiker zelf focust": htmx focust bij
  // elke swap het eerste [autofocus]-veld, en een klik op Opslaan focust die
  // knop. Dat zijn stappen in dezelfde flow, geen afwijkingen ervan. Dat de
  // focus van de gebruiker gerespecteerd wordt regelt de voorwaarde hieronder:
  // stond hij ergens anders dan op <body>, dan blijven we eraf.

  document.addEventListener("htmx:afterSettle", (event) => {
    const active = document.activeElement;
    if (
      active &&
      active !== document.body &&
      active !== document.documentElement
    )
      return;

    const container = event.detail.target;
    if (!container || typeof container.querySelector !== "function") return;

    if (
      container.matches("[autofocus]") ||
      container.querySelector("[autofocus]")
    )
      return;

    if (focusFromTrail()) return;

    // De container is normaal niet focusbaar; -1 laat hem wel focus ontvangen
    // zonder hem in de tabvolgorde te zetten.
    if (!container.hasAttribute("tabindex"))
      container.setAttribute("tabindex", "-1");
    container.focus();
  });
})();
