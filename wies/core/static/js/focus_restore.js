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
//   0. Kwam er een afgekeurd formulier terug, dan naar het veld met de fout.
//      Daar moet de gebruiker zijn; hem op het eerste veld zetten laat hem de
//      fout zelf zoeken. Als enige stap ongeacht muis of toetsenbord, en
//      ongeacht waar de focus stond: er is iets veranderd aan waar hij moet
//      zijn, en de fout hoeft niet in beeld te staan.
//   1. Verder alleen ingrijpen als de focus echt naar <body> is gevallen. Bleef
//      hij ergens staan (zoeken en filteren verversen de lijst terwijl je in
//      het zoekveld staat), dan is er niets aan de hand en blijven we eraf.
//   2. Zette de server [autofocus] in de nieuwe inhoud, dan heeft htmx die al
//      gefocust en weet de server het beter dan wij.
//   3. Terug naar het meest recente element dat een swap veroorzaakte en dat we
//      in de huidige inhoud kunnen terugvinden.
//   4. Anders het eerste bedienbare element in de nieuwe inhoud, zodat je
//      bovenaan die inhoud staat in plaats van bovenaan de pagina.
//
// Waarom stap 3 een stapel is en niet één element: een opslag die met
// HX-Location terugspringt levert drie swaps op. Je drukt "Periode wijzigen"
// (swap 1), je dient het formulier in (swap 2), en htmx haalt daarna zelf het
// paneel opnieuw op (swap 3). Die laatste heeft geen bronelement -- htmx roept
// intern `ajax("get", ...)` aan, dus `requestConfig.elt` is `document.body`.
// De knop waar je vandaan kwam zit dan twee stappen terug.
//
// Stap 1 tot en met 4 gelden alleen voor toetsenbordgebruik: wie net geklikt
// heeft weet waar hij is en heeft geen bestemming nodig. Stap 0 staat daarbuiten
// -- een afkeuring verplaatst waar de gebruiker moet zijn, ook als hij klikte.
(function () {
  "use strict";

  // Op volgorde van betrouwbaarheid. Een id is uniek; een URL identificeert de
  // actie, wat voor deze panelen net zo goed werkt en niets van de templates
  // vraagt. Een verwijzing naar de node zelf is waardeloos: die is na een
  // opnieuw opgehaald paneel losgekoppeld.
  const IDENTIFYING_ATTRIBUTES = ["id", "hx-get", "hx-post", "href"];

  // Wat een gebruiker kan bedienen. De custom elements erbij omdat de NLDD-
  // componenten hun echte control in een shadow root zetten: `nldd-button`
  // matcht geen enkele standaardselector, maar is wel een tabstop.
  // Muis of toetsenbord? Dezelfde vraag die de browser zelf beantwoordt voor
  // :focus-visible, maar die staat ons niet ter beschikking. Klikken is een
  // aanwijsactie: de gebruiker weet waar hij is en heeft geen bestemming nodig.
  // Alleen wie met het toetsenbord werkt raakt zijn plek kwijt als de focus valt.
  let laatsteInvoer = "toetsenbord";
  document.addEventListener(
    "keydown",
    () => (laatsteInvoer = "toetsenbord"),
    true,
  );
  document.addEventListener(
    "pointerdown",
    () => (laatsteInvoer = "muis"),
    true,
  );

  const FOCUSABLE = [
    "a[href]",
    "button",
    "input:not([type=hidden])",
    "select",
    "textarea",
    "[tabindex]:not([tabindex='-1'])",
    "nldd-button",
    "nldd-icon-button",
    "nldd-link",
    "nldd-list-item[href]",
    "nldd-search-field",
    // Invoervelden staan vóór de knoppen in een formulier, maar matchten geen
    // enkele selector hierboven: hun echte control zit in een shadow root. Zonder
    // deze regels sloeg "eerste bedienbare element" alle velden over en landde de
    // focus op de eerste knop, halverwege het formulier.
    //
    // Alleen componenten die focus() ook echt accepteren -- via delegatesFocus of
    // een eigen focus()-override. De rest (nldd-checkbox, nldd-radio-button en de
    // -field-varianten, nldd-segmented-control) heeft geen van beide: focus()
    // erop doet stil niets. Die staan hier bewust niet, want een selector die
    // matcht maar niet focust is erger dan geen match -- hij verdringt een
    // element verderop dat het wel had gekund.
    //
    // nldd-dropdown ontbreekt met opzet: dat component wikkelt een echte
    // <select> in light DOM, die "select" hierboven al matcht. De host staat er
    // in documentvolgorde vóór en zou die match dus wegkapen.
    "nldd-text-field",
    "nldd-multi-line-text-field",
    "nldd-date-field",
    "nldd-number-field",
    "nldd-password-field",
    "nldd-combo-box",
    "nldd-token-field",
    "nldd-switch",
    // Navigatie-items met een eigen focus()-override. Bij de tabbar geldt een
    // roving tabindex: alleen de geselecteerde tab is de ingang, de rest staat
    // op tabindex="-1" en hoort dus niet gefocust te worden. Die tabindex zit
    // in de shadow root, dus de selector hierboven ziet hem niet -- vandaar
    // [selected]. nldd-toolbar-item en nldd-segmented-control-item hebben geen
    // override en blijven eruit.
    "nldd-tab-bar-item[selected]",
    "nldd-menu-bar-item",
  ].join(",");

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

  // Doorlopen tot er een pakt: een component kan matchen en de focus toch
  // weigeren (geen delegatesFocus, geen eigen focus()). Stoppen bij de eerste
  // match zou de focus stil op <body> laten staan -- precies wat dit script
  // moet voorkomen.
  function focusFirst(elements, { preventScroll = true } = {}) {
    for (const element of elements) {
      if (!isVisible(element) || typeof element.focus !== "function") continue;
      element.focus({ preventScroll });
      if (focusTook(element)) return true;
    }
    return false;
  }

  function focusFromTrail() {
    for (let index = 0; index < trail.length; index++) {
      const element = resolve(trail[index]);
      if (!element || typeof element.focus !== "function") continue;
      element.focus({ preventScroll: true });
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
    const container = event.detail.target;
    if (!container || typeof container.querySelector !== "function") return;

    // Een afgekeurd formulier komt terug met de fout erin. Dan is de eerste
    // bedienbare plek niet waar je moet zijn: je wilt naar het veld dat
    // afgekeurd is, anders moet je de fout zelf gaan zoeken.
    //
    // Als enige stap ook voor de muisgebruiker, en ook als de focus nog ergens
    // staat. De regels hieronder gaan ervan uit dat er niets veranderd is aan
    // waar de gebruiker moet zijn -- bij een afkeuring is dat juist wel zo. De
    // fout hoeft niet in beeld te staan: bij een langer formulier of een klein
    // venster staat hij eronder, en dan is "wie klikt weet waar hij is" niet
    // meer waar.
    //
    // `invalid` is de conventie van wire_field_errors(): elk widget zet het op
    // het element dat nldd-form-field._findInput() teruggeeft, dus precies het
    // element dat de fout draagt. Het component reflecteert de property naar
    // het attribuut, en de server rendert het al als HTML, dus dit werkt ook
    // voordat Lit is opgestart. De error-tekst krijgt `invalid` ook, maar is
    // geen invoer en hoort de focus niet te krijgen.
    //
    // Wel preventScroll weglaten, anders zie je niet waar je heen gestuurd bent.
    const invalid = container.querySelectorAll(
      "[invalid]:not(nldd-form-field-error-text)",
    );
    if (invalid.length && focusFirst(invalid, { preventScroll: false })) return;

    // Wie klikt, stoort niet: de focus verplaatsen naar een element waar de
    // muis niet is levert die gebruiker niets op. Drukt hij daarna Tab, dan
    // begint hij bovenaan, en dat is wat een muisgebruiker ook zonder dit
    // script gewend is.
    if (laatsteInvoer === "muis") return;

    const active = document.activeElement;
    if (
      active &&
      active !== document.body &&
      active !== document.documentElement
    )
      return;

    if (
      container.matches("[autofocus]") ||
      container.querySelector("[autofocus]")
    )
      return;

    if (focusFromTrail()) return;

    // Het eerste bedienbare element in de nieuwe inhoud, en uitdrukkelijk niet
    // de container zelf.
    //
    // De container is een component (`nldd-page`, `nldd-sheet`) en dus een
    // shadow host. Die is niet focusbaar (`delegatesFocus` staat op false, dus
    // `focus()` erop doet niets), en hem focusbaar maken met tabindex="-1"
    // heeft een prijs: bij een shadow host bepaalt de tabindex van de host of
    // zijn inhoud meedoet in de tabvolgorde. Gemeten op het zijpaneel: mét dat
    // attribuut loopt Tab nog één ronde en blijft daarna op <body> hangen, en
    // Shift+Tab komt de inhoud helemaal niet meer in. Het attribuut werd ook
    // nooit opgeruimd, dus één swap brak het paneel voor de rest van de
    // paginalevensduur.
    //
    // De elementen binnen de container zijn wel gewoon focusbaar en staan al in
    // de tabvolgorde, dus daar landen we op. Pakt geen enkele, dan doen we
    // niets: de focus op <body> laten staan is beter dan de tabvolgorde slopen.
    focusFirst(container.querySelectorAll(FOCUSABLE));
  });
})();
