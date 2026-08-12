# Changes

This files lists the changes during the lifetime of this project.

## unreleased

- de cursor staat meteen in het naamveld als je de sheet "Merk toevoegen" of "Bewerk merk" opent, zoals bij labels al gebeurde. Niet na een validatiefout: dan blijft de focus bij het veld met de fout in plaats van naar boven te springen
- NLDD bijgewerkt naar 0.8.82: Enter in een invoerveld verstuurt het formulier nu vanuit het design system zelf, voor alle enkelregelige velden (tekst, datum, tijd, nummer, wachtwoord, combo box, token field). De tijdelijke workaround in `enter_submits.js` is daarmee weg. Het component volgt bovendien de spec-regel die de workaround niet had: zonder submit-knop verstuurt Enter alleen als het formulier één veld heeft
- de melding dat iets beperkt zichtbaar is, is nu overal dezelfde oranje chip "Beperkt zichtbaar" met een doorgestreept oog; de volledige zin ("Alleen zichtbaar voor jou en …") staat in de tooltip. Hij stond eerder in drie vormen door de app: als losse regel onder een opdrachtkaart, en in het opdrachtpaneel ingebed in een omhullende tekst ("De geplaatste teamleden zijn …") met een kleingemaakte eerste letter, in dezelfde alinea als de melding over de externe bron. Op de kaarten staat de chip nu bij de andere tags in plaats van als aparte regel, waardoor de chevron weer op zijn gewone plek terugkomt; in het opdrachtpaneel naast de "Toevoegen"-knop. Nieuw is de chip op de Updates-tijdlijn: die toont teamwijzigingen ongefilterd aan de Business Manager, maar liet niet zien dat anderen die regels juist niet krijgen — alleen op teamregels, want de overige velden zijn voor iedereen gelijk. De variant voor een afgelopen opdracht waar je BM was ("… jou en het team") stond hardcoded in de view en is verhuisd naar `placement_visibility.py`, waar de andere twee al stonden
- fix dat de terugknop van het zijpaneel na het opslaan van een veld naar het formulier wees dat je net had afgerond ("Opdrachtperiode wijzigen"). Het bewerkformulier keert via HX-Location terug naar het ouderpaneel; die GET telde als een stap dieper in plaats van een stap terug, waardoor de bewerkstap als 'vorige' op de stack bleef staan
- de actie "Profiel bekijken" is uit het rijmenu van de gebruikerslijst verdwenen. Hij werkte al niet meer sinds de public_id-migratie (de view zocht nog op een numerieke id, terwijl het menu een UUID meestuurde), en verscheen bovendien alleen bij gebruikers met een gekoppelde collega — in de praktijk vrijwel niemand. Het zijpaneel op die beheerpagina bestond alleen voor deze actie en is mee opgeruimd
- 580: `/` (Wie zit waar?), `/opdrachten/` (Aanvragen) en `/profiel/` (Mijn profiel) hebben weer een `<h1>`. Bij de NLDD-omzetting verving een `nldd-toolbar` met zoekveld en filterknop de hele paginakop, zonder vervangende kop, waardoor de koppenstructuur van die drie pagina's pas bij een `<h3>` in de zijbalk begon. Een pagina hoort een kop op het hoogste niveau te hebben, en schermlezergebruikers navigeren juist op koppen. Op het profiel zit de kop in het `header`-slot van de sectie en niet erboven: die pagina heeft geen zijbalk, en buiten de sectie is er geen horizontale marge, dus daar zou de kop tegen de vensterrand plakken
- de Van/Naar-waarden op de Updates-tijdlijn gebruiken nu dezelfde weergave als de opdrachtomschrijving: elk als eigen blok onder de zin in plaats van als lopende tekst erachter, met regelovergangen die blijven staan en een echte NLDD-knop voor "Toon meer". Die tijdlijn had nog een tweede, eigen schakelaar met een kale `<button>` waarvan de opmaak met de RVO-stylesheet was verdwenen; die implementatie (`show_more.js` plus de `show-more`-handler) is nu weg, er is er nog één
- het decoratieve vinkje in een filterrij gebruikt nu het `decorative`-attribuut van `nldd-checkbox` in plaats van `aria-hidden="true" tabindex="-1"`. Die twee bereiken de shadow root niet, dus het `<input>` daarbinnen bleef bestaan en focusbaar, binnen een rij-knop die zelf al `role="checkbox"` draagt. Met `decorative` rendert de component dat veld niet meer. Ruimt 30 axe-schendingen op (`aria-hidden-focus` en `nested-interactive`) op de plaatsingen- en opdrachtenlijst
- fix dat het bewerken van een opdracht de Business Manager wiste. De keuzelijst bevatte alleen collega's uit de groep "Business Development Manager"; stond de huidige eigenaar daar niet in — wat voor vrijwel elke opdracht gold — dan had de combo box geen optie die bij zijn waarde paste, rendeerde het veld leeg en poste opslaan een lege waarde. De huidige eigenaar staat nu altijd in de lijst, ook buiten die groep; bij het aanmaken van een opdracht (nog geen eigenaar) blijft de lijst tot de groep beperkt. Daarvoor mag een `choices`-callable van een editable voortaan het object aannemen dat bewerkt wordt
- 576: opdrachtomschrijvingen respecteren weer hun regelovergangen en worden weer ingekort met een "Toon meer"-schakelaar. De opmaak hiervoor (`white-space: pre-wrap` op de tekst en de styling van de knop) hoorde bij de RVO-stylesheet en verdween met het opruimen daarvan, terwijl de templates en `inline_edit.js` bleven staan — nu terug in NLDD-tokens. Daarnaast stond de omschrijving in het opdrachtpaneel en de onboardingbox als kale `<p>` bóven de gegevens: een lange tekst duwde daar de tabs en alle velden naar beneden, terwijl hij inhoudelijk buiten het tabblad "Gegevens" viel. Hij staat nu weer als rij "Opdrachtomschrijving" in de gegevenslijst (zoals vóór de NLDD-migratie), met een eigen bewerk-actie in het ⋯-menu van die rij
- 553: Escape sluit de onboardingwizard weer alleen voor nu — bij de volgende pagina staat hij er gewoon weer, zoals vóór de NLDD-migratie. Alleen de knop in de titelbalk vinkt de onboarding definitief af, en die heet weer "Overslaan" in plaats van "Sluit". De wizard luisterde naar de `close` van het venster, maar `nldd-window` sluit zichzelf op zowel Escape als de dismiss-knop, waardoor die twee niet meer uit elkaar te houden waren en één Escape je onboarding permanent wegvinkte

- klikbare kaarten (opdracht- en collega-opdrachtkaarten) kleuren nu licht op bij hover. `nldd-card` tekent zelf alleen een focusring en een pointer-cursor, geen hover-staat, terwijl de hele kaart een link is. Alleen kaarten met `href`/`button` krijgen 'm, zodat de cijferkaarten op het staff-dashboard niet klikbaar gaan lijken
- 427: heeft een opdracht naast de primaire opdrachtgever ook een betrokken partij, dan krijgt elke opdrachtgever nu een eigen rij met een eigen acties-menu, zodat je ook op de tweede opdrachtgever (en elk niveau van háár hiërarchie) kunt filteren. Eerder kende het veld één menu dat altijd de eerste rij volgde, waardoor de tweede opdrachtgever onbereikbaar was. Elke rij toont welke rol hij heeft — (primair) of (betrokken) — maar alleen als er meer dan één opdrachtgever is, en het ⋯-menu draagt de naam van zijn eigen organisatie zodat de menu's uit elkaar te houden zijn. Elk menu heeft dezelfde opbouw ("Opdrachtgever wijzigen" + "Bekijk opdrachten"): twee ⋯-knoppen naast elkaar die stilletjes van elkaar verschillen zijn een raadsel — je klikt op de tweede, verwacht "wijzigen" en krijgt niets. Het formulier bewerkt nog steeds alle opdrachtgevers tegelijk; dat blijkt uit het formulier zelf en hoeft niet in het label te staan
- 427: in het opdrachtpaneel opent "Bekijk opdrachten" (in het opdrachtgever-menu) nu een submenu met een niveau per hiërarchie-stap (Datafundamenten › DGBD › Fin), zodat je net als vroeger met de klikbare breadcrumb op elk niveau kunt filteren. De enkele "Bekijk alle opdrachten" filterde alleen op de laagste node — juist de eenheid die de minste andere opdrachten deelt
- 427: opdrachtgeverfilter: alleen een door de gebruiker zelf gekozen rij in de boom krijgt de grijze achtergrond; een parent die alleen aanstaat doordat zijn kinderen aanstaan toont een streepje (indeterminate), geen grijs. De grijze rij komt nu van het `selected`-attribuut van het list-item (niet van de checkbox-checked-fill, die elke aangevinkte rij grijs maakte — ook een meegecascade kind — en niet per rij te onderdrukken is). Daarvoor is de selecteerbare rij een `button`-actie met een decoratief vinkje i.p.v. een checkbox-actie; de knop krijgt `role="checkbox"` + `aria-checked` (aan/streepje/uit) zodat de toegankelijkheid klopt. Geen dikgedrukte labels of accentkleur meer, en geen enkele design-system-variabele wordt nog overschreven. De top-3 van elke filtergroep (opdrachtgever, rol, labels, merk) is vast op count: een optie aanvinken verspringt of verdringt niets meer — een keuze buiten de top-3 komt er onderaan bij. De filterzijbalk springt niet meer naar boven na een filterwijziging (scrollpositie van de sidebar-box wordt bewaard)
- 544: de gebruikerslijst toont de rol(len) weer als tag achter de naam, en de "Filters"-knop opent een zijsheet om op rol, expertise, thema en merk te filteren — hetzelfde filtersysteem als de opdrachten/plaatsingen-lijst (top-3 per groep + "Meer…", live filteren bij aanvinken), maar altijd als sheet zodat de beheer-navigatie in de zijbalk blijft. Rol is nu een meervoudig filter (checkboxes) zodat het in datzelfde systeem past. De filter-backend bestond al in `UserListView`; alleen de rol-kolom en de filter-UI waren bij de NLDD-migratie verdwenen
- 427: in de detailpanelen tonen rij-acties bij één actie het actie-icoon direct (met tooltip), en bij meerdere een puntjes-menu — consistent in het opdracht- én plaatsingpaneel via één gedeelde `render_row_actions`-macro. De paneel-toolbar (Gegevens bewerken / Opdracht verwijderen) is nu een echt NLDD-overflowmenu dat bij smalle breedte samenvouwt in één `…`-knop
- 427: de opdrachtkaart op de Aanvragen-lijst is weer een echte link (`href` + `hx_link_guard`) i.p.v. een knop, zodat ⌘/middenklik de opdracht in een nieuw tabblad opent — consistent met de plaatsing- en collega-kaarten
- 427: fix dat de aantallen naast de opdrachtgevers nu wel updaten met de andere actieve filters
- 427: verwijder het losstaande full-page opdracht-/teamformulier nu de NLDD-sheets die rol overnemen. Het team van een opdracht is niet langer een inline-bewerkbare collectie: het wordt getoond via zijn `display` en bewerkt via de per-lid-zijsheet (`assignment_member_edit_view`), dus de generieke inline-edit-opslag geldt er niet meer voor (save/edit-GET op zo'n read-only collectie geeft nu 404). Weg: `AssignmentCreateForm`, de team-form-partials (`assignment_services_form.html`, `service_row.html`), de eigen `assignment_form.js`/`.css`, en de modale `label-category-create`/`-edit`-views + hun URLs (bewerken loopt nu via de labels-sheet). `EditableCollection.save` is optioneel geworden voor precies deze read-only collecties
- TODO: migreer de Merken-beheerpagina (`/beheer/merken/`) van de oude RVO/jinja-roos-componenten naar de NLDD web components, gelijk aan de Labels-pagina. De pagina rendert weer een echte lijst met knoppen (was kaal geworden nadat de RVO-componenten van deze branch verdwenen). Toevoegen én bewerken lopen nu via een zijsheet ("Merk toevoegen") met een more-menu per rij voor Bewerken/Verwijderen, in plaats van het inline-formulier onderaan
- 555: verwijder de losstaande full-page "opdracht aanmaken" (`/opdrachten/aanmaken/`). Sinds de sheet ("Opdracht invoeren") de knop overnam was die pagina alleen nog via de directe URL bereikbaar. Het gedeelde opdracht-/rollenformulier blijft, want de inline-edit van het opdrachtteam gebruikt het
- TODO: fix dat labels die je in de onboarding (stap "Vul je profiel aan") koos niet in je profiel werden opgeslagen. Twee oorzaken: (1) de bare `inline_edit_form`-macro zette geen concurrency-token, waardoor de opslag-view elke save als conflict weigerde; (2) het token per `labels_<categorie>` hashte álle labels in plaats van alleen die categorie, dus bij meerdere categorieën maakte de eerste save de tokens van de rest stale — alleen één categorie werd bewaard. De macro geeft het token nu mee, en het label-editable filtert zijn beginwaarde per categorie (symmetrisch met de save), zodat alle categorieën tegelijk opslaan

- TODO: "Wis alle filters" is terug naast de filter-chips — die knop was verdwenen toen `filter_chips.html` bij de NLDD-migratie werd opgeruimd (de handler-comment bleef achter, maar knop én logica waren weg). Eén klik leegt nu weer alle actieve filters (zoek, rol/labels, datum) tegelijk
- TODO: "Opdracht invoeren" opent nu de aanmaak in het zijpaneel in plaats van een aparte pagina — je vult naam, omschrijving, opdrachtgever, periode en Business Manager in, en na "Aanmaken" land je direct in het opdrachtpaneel waar je de rollen/aanvragen toevoegt. Een "Opdracht is aangemaakt"-banner (met een "Bekijk opdracht"-link) reist als OOB-swap mee met dat paneel, want de zijpaneel-swap herlaadt de pagina niet. De full-page `assignment-create` blijft bestaan; alleen de knop op de Aanvragen-lijst opent voortaan de sheet
- TODO: fix dat de link-tekst in een flash-banner werd afgekapt bij de eerste spatie ("Bekijk opdracht" werd "Bekijk") — de `parse_message_link`-filter splitste de tag op witruimte
- TODO: fix dat de opdrachtgever-picker in de "Opdracht invoeren"/-bewerken-sheet direct weer sloot na openen — twee geneste modale sheets stapelen op de top-layer en de omringende sheet slikte de open-klik in als achtergrond-klik. De picker wordt nu naar `<body>` gehesen vóór openen (op de full-page zonder omringende sheet is dat een no-op)
- TODO: fix dat de foutmelding "Voeg minimaal 1 opdrachtgever toe." onzichtbaar was bij het aanmaken/bewerken van een opdracht — leek alsof "Aanmaken"/"Opslaan" niks deed. De opdrachtgever-picker en de opdracht-sheets renderden de fout los, zonder de id-koppeling die `nldd-form-field` nodig heeft; nu via `as_field_group()` + `wire_field_errors`, waardoor de melding zichtbaar wordt (stond op hoogte 0)
- 427: fix dat de open lijst van een keuzeveld (native `<select>`) in donkere modus wit-op-wit was op Windows/Chrome (#529) — de browser kende de `color-scheme` niet bij een expliciet gekozen thema, dus de OS-popup pakte wel de tekst- maar niet de achtergrondkleur. `color-scheme` volgt nu het `data-scheme`-attribuut op `<html>` (kleurt meteen ook date-pickers en scrollbars mee)
- 427: (migration) add theming (dark mode/light mode)
- 427: NLDD: fix dat het opslaan van een gewijzigde plaatsing (rol/periode) in het zijpaneel een 500 gaf — de opslag riep een niet-bestaande functie aan; de plaatsingswijziging wordt nu net als voorheen als "Team"-gebeurtenis op de tijdlijn van de opdracht gespiegeld
- 427: NLDD: verwijder de parallelle `/ndd/`-PoC-laag nu de hoofdroutes op het NLDD Design System draaien; de beheer-opslagacties (gebruiker/label/profiel) verwijzen niet langer stiekem naar die laag maar naar de gewone routes
- 427: NLDD: date- en keuzevelden tonen hun validatiefout weer zichtbaar (het datumveld koppelde de fout via het verkeerde attribuut, waardoor de melding op hoogte 0 stond)
- 427: NLDD: fix modals never opening (Beheer > Labels: "Categorie toevoegen" and the pencil icons did nothing). `nldd-window.show()` reads the native `<dialog>` out of its shadow root and returns silently when it isn't there yet — right after an htmx swap the element is upgraded but Lit has not rendered, so `dialog.js` opened nothing. It now awaits `updateComplete` first
- 427: NLDD: replace `click_bridge.js` with `hx_link_guard.js`. The bridge forwarded clicks on `nldd-*` elements carrying `hx-*` to htmx, which htmx 2 already does itself — so it only added a second, duplicate request per click (duplicate POSTs on submits). What it _also_ did, and what is still needed, is suppress the default action on rows that carry both `href` and `hx-get` (`nldd-list-item` in the gebruikers, plaatsingen and labels lists): those keep a real href for link semantics, but the anchor in the component's shadow root would otherwise navigate and throw the modal away. The guard now does only that, in the capture phase, leaving modified clicks (ctrl/cmd/middle) to work as ordinary links
- 427: NLDD: het datumveld gebruikt het echte `nldd-date-field` (nieuw in 0.8.70), de laatste widget die nog native HTML was. Het component leest een getypte datum ruimhartig (`12-3-2026`, `12/03/2026`, ISO) en normaliseert bij blur, en zet zijn eigen kalenderknop in de plaats van de browser-datepicker — die in Safari niet te sluiten was. Form-associated met een ISO-waarde, dus `DateInput(format="%Y-%m-%d")` blijft kloppen. Ook de twee losse "Nieuw label"-invoervelden zijn nu `nldd-text-field`
- 427: NLDD: upgrade naar 0.8.70 en vervang de handgebouwde avatar-cirkels door het echte `nldd-avatar` (nieuw in 0.8.69). Het component leidt de initialen zelf af uit `name` — waar wij één letter toonden staat er nu "PW" / "AJ" — schaalt brede initialen automatisch terug en valt bij een naamloze vacature terug op het person-icoon in plaats van een "?". Alle negen plekken (tabellen, panels, kaarten, tijdlijn) gaan om; de eigen avatar-CSS is vervallen. Van de vier breaking changes in 0.8.67–0.8.70 raakt er geen enkele deze codebase (gecontroleerd: content-colour tokens, `--context-cell-content-*`, `slot="menu"` en de `batch`→`badge` icoonnamen)
- 427: NLDD: opdrachtkaarten en de teamlijst gebruiken nu echte componenten. De kaarten waren een `<a>` met handgebouwde rand, radius en hover — nu `nldd-collection` + `nldd-card`, dat de kaartrand, hover en de overlay-link zelf levert. De teamrijen waren losse divs en zijn nu `nldd-list` met `nldd-list-item` + cellen, precies het patroon dat het design system voorschrijft. Drie bijna-identieke kopieën van het kaartblok (collega-panel, plaatsing-panel, profielpagina) lopen nu door één partial. De avatar blijft eigen CSS: NLDD heeft geen avatar-component
- 427: NLDD: fix dat validatiefouten onzichtbaar waren. `nldd-form-field` toont een `nldd-form-field-error-text` alleen wanneer de input `invalid` reflecteert én de fout bij id noemt in `error-message`; die koppeling ontbrak, dus de meldingen stonden wel in de DOM maar met hoogte 0 — een gebruiker zag geen enkele reden waarom opslaan mislukte, en screenreaders kondigden niets aan. De veldtemplate wiret ze nu via `wire_field_errors()`, en de tests controleren de koppeling in plaats van de losse tag
- 427: NLDD: verwijder `parts/filter_chips.html` — dood: nergens geïncludeerd, geen CSS, en de `filter-remove`-knoppen hadden geen handler. De echte filterchips draaien al op `nldd-token` in `filter_and_table_container.html`
- 427: NLDD: het side panel heeft een sluitknop. Twee van de drie panels (plaatsing, opdracht) hadden er helemaal geen — sluiten kon alleen via ESC of een klik op de achtergrond; het derde (collega) had een handgebouwde `<button>`. Alle drie gebruiken nu een echte `nldd-top-title-bar` met `dismiss-text="Sluiten"`, waarop `nldd-sheet` zichzelf sluit zonder extra JavaScript. De nagebouwde `.nldd-panel__bar` CSS en de `panel-close` click-handler zijn daarmee vervallen
- 427: NLDD: labels zijn weer te kiezen op de gebruiker-bewerken-pagina, via een echte `nldd-token-field`. De oude multiselect was handgebouwd zonder bijbehorende JS of CSS: de dropdown ging nooit open, dus labels waren niet te wijzigen. Nu filtert typen de lijst en worden gekozen labels verwijderbare tokens. Het component is form-associated en stuurt één entry per waarde onder dezelfde `name`, precies wat Django's `getlist()` verwacht
- 427: NLDD: fix dat checkbox- en radiovelden hun waarde niet meesturen bij opslaan. `nldd-checkbox-field`/`nldd-radio-button-field` renderen hun label netjes, maar houden het form-associated element in hun shadow root — en zo'n element hoort alleen bij het formulier waar het in de light DOM van staat. Gevolg: `groups`, de label-categorieën en de kleur van een labelcategorie ontbraken volledig in de POST, waardoor opslaan die velden leegde. Nu `nldd-checkbox`/`nldd-radio-button` rechtstreeks, met een eigen `<label>` ernaast
- 427: NLDD: form widgets that only looked like design-system components are now real ones — select becomes `nldd-dropdown` (a wrapper around the native `<select>`, so submission and keyboard handling stay with the browser), checkboxes become `nldd-checkbox`/`nldd-checkbox-field` and radios `nldd-radio-button-group`/`-field`, which also gives radio groups the arrow-key navigation they lacked and drops a duplicate-`id` bug where every radio in a group shared one id. The `nldd-*` names were CSS classes on plain `<div>`s, so the gap was invisible in the inspector. Selects now carry an `aria-label` from their field label: `nldd-form-field` labels only its first child, which for a dropdown is the wrapper, so the inner `<select>` was left unnamed for screen readers. `date` (needs a newer design-system than 0.8.66) and the bespoke multiselect stay native for now
- 427: NLDD: the "Over deze site"-links (Privacy, Toegankelijkheid, Contact) moved from a general sidebar into a real `nldd-page-footer` legal bar in `base.html`, so they are reachable from every page instead of only the few that included that sidebar. Drops `parts/general_sidebar.html`, whose primary navigation only duplicated the top menu bar; `{% block sidebar %}` stays for pages with genuinely contextual sidebars (filters, beheer-nav)
- 427: NLDD: split the former `htmx-bridge.js` — now that filters submit natively, the file was filter-interaction glue, not a bridge. Renamed to `filter_interactions.js` and extracted the two standalone pieces (`click_bridge.js` for nldd-_ hx-_ forwarding, `sidebar_toggle.js`) into their own modules
- 427: NLDD: filter checkboxes now submit natively — each carries its own `name` + `data-filter-input`, so `hx-include` sends repeated params (`rol=1&rol=2`) straight to the view's `getlist`. Drops the hidden-input mirroring from `htmx-bridge.js` (the `rebuildCheckboxesIn`/`attachTextField` shadow-input machinery); the "Meer"-modal keeps a small overflow slot only for picks that have no inline checkbox
- 427: NLDD: keyboard navigation for the opdrachtgever tree (WAI-ARIA Treeview — arrow keys, Home/End, role="tree"/treeitem/group)
- 427: NLDD: bring the filter/search UX to parity with `main`/#402 — a "Wis alle filters" button next to the active chips (also clears the search), the opdrachtgever filter's inline top-3 quick checkboxes (`org`/`org_self`/`org_type`) alongside the "Meer" tree modal, a magnifier icon on the "Meer" buttons, and a full search experience (Enter-to-commit, live suggestions dropdown with a "Zoeken op …" action and opdrachtgever suggestions). Also fixes individual filter chips not being dismissable (a `data-nldd-dismiss` dataset-key mismatch) and a dead `updateOrgFilterButtonText()` call that aborted the client-modal apply.
- 427: NLDD: adopt the `nldd-sidebar-section` layout on every page (upgrade @nldd/design-system to 0.8.64) — a sticky sidebar on wide screens that collapses to a sheet on narrow ones; contextual sidebars everywhere (filters, beheer-nav, general nav)
- 427: NLDD: port the filter "Meer"-modal UX (#402) — each filter group shows its top-3 options plus a "Meer" button that opens the full alphabetical list in a modal with search; the selection applies only on "Filter toepassen"
- 427: NLDD: merge `main` into the NLDD design-system branch — adopt the opdracht/plaatsing side-panel features (Gegevens/Updates tabs, inline-edit of all fields, opdracht verwijderen, placement periods), the "Dubbele opdrachten samenvoegen" beheertool and the full privacyverklaring, all rebuilt in the NLDD design system; migrate the privacy-html generator to NLDD output
- ?
- 525: logging in no longer dead-ends on a 500 page when the login callback fails, whatever the cause. The most common one is Keycloak having lost its authentication session (for example because the login screen was left open for too long); the login is then restarted once automatically, and if that fails as well the user gets a page explaining what happened. Any other failure gets its own page pointing at support, and is still reported to the team.
- 525: the "geen toegang" page pointed at wies-support@rijksoverheid.nl, which does not exist; it now points at wies-odi@rijksoverheid.nl
- 474: URLs and filters now use a uuid identifier instead of the sequential id, so records and overviews can no longer be enumerated by incrementing ids.
- 474: A filter value that matches nothing now shows a chip ("Onbekende rol", "Onbekend label", "Onbekend merk", "Onbekende opdrachtgever").

## 2026-08-04

- 463: (migration)(post-release actions) change "merk" to be a single select. "merk" now has its own table (`suborganization`).
- 463: make test actions more robust (work with newer versions of node and other location of djlint)
- 426: (migration)(post-release actions) log the client request metadata on audit and login events (BIO device logging). Removed the staff "Debug: request metadata" page
- 426: logout events are now logged alongside logins
- 503: fix the "Wie zit waar?", opdrachten and profiel overviews returning a 500 error when the side-panel `plaatsing`, `collega` or `opdracht` parameter contained a non-numeric value in the URL
- 503: fix opdracht aanmaken returning a 500 error instead of a validation message when the submitted form data contained a non-numeric service count
- 501: de opdracht-CSV-import maakt nieuwe collega's alleen nog aan als hun e-mailadres een toegestaan domein heeft (net als elders in de app); bestaande collega's (bijvoorbeeld uit OTYS) met een ander domein blijven gewoon bruikbaar.
- 483: inline editing now detects concurrent edits instead of silently overwriting. If the data changed since you opened the edit form, the form comes back with a warning that names the field and the value someone else entered, keeping your own input; Opslaan saves anyway, Annuleren shows the changed data. This covers every inline-editable field (including the team and period forms), and an edit submitted without the form's token (for example a page left open across a deploy) is likewise held back with the same warning instead of saved unverified.
- 480: the OIDC login now uses PKCE (S256) in the authorization-code flow. The government OIDC profile (OIDC-NLGov, sections 4.1 and 4.2.1) requires this for every client: https://gitdocumentatie.logius.nl/publicatie/api/oidc/
- 453: the statistics pages shows unique logins per day in stead of the total number of logins
- 498: harden ci: pin actions on sha, explicit permissions per action stage

## 2026-07-23

- 473: fix the opdrachtgever filter counts including planned placements that placement visibility hides from unrelated viewers
- 473: stop the inline-edit endpoint from revealing whether an object exists to users who may not edit it (a missing and a forbidden object now return the same response)
- 478: the user and opdracht CSV imports now reject files larger than 50 MB, so an extremely large file cannot exhaust a worker's memory
- 477: logging out is now only possible via the button (POST), no longer via a bare GET request
- 481: the production container no longer silently falls back to the local development settings (DEBUG on) when DJANGO_SETTINGS_MODULE is missing at startup; the startup script then defaults to the production settings (an explicitly provided value still takes precedence)
- 486: the opdracht and user CSV imports now show a graceful error message instead of a 500 when a value is too long for its field or the file is not valid CSV.
- 479: fix the "Wie zit waar?" and Gebruikers overviews returning a 500 error and showing "Wis filters" when the labels filter contained a non-numeric value in the URL
- 491: PR preview environments are now reliably removed when a PR closes and a preview can be rebuilt manually from the Actions UI; the weekly registry cleanup of old preview images is fixed
- 460: (migration)(add env vars) basic error monitoring — unhandled server errors (500) and failed background tasks are stored and shown on the statistics page, with a Mattermost notification.
- 460: A failing task is marked failed immediately instead of hanging until timeout.
- 493: (remove env vars) the background worker now runs on its own settings module (config.settings.worker) and no longer requires the OIDC credentials to be set at startup. locally worker now also uses its own dedicate .env file
- 494: add trivy container scanning as recurring action
- 482: the Content-Security-Policy for scripts no longer allows inline JavaScript (`script-src 'self'`). All scripts and click/keyboard handling have been moved to external JS files
- 482: the htmx history cache is now disabled on all pages instead of only on the assignments overview and the placements table; navigating back now always fetches a page fresh everywhere.
- 496: fix the PR preview cleanup never running: its first step called `gh` without `--repo` in a job that has no checkout, so it failed immediately and the ZAD deployment and PR-tagged images of every closed PR were left behind
- 497: bumped dev/CI dependencies and GitHub Actions
- 497: the production images (web/worker) no longer contain dev/test tooling, reducing the runtime attack surface
- 479: fix the "Wie zit waar?" and Gebruikers overviews returning a 500 error and showing "Wis filters" when the labels filter contained a non-numeric value in the URL; such a value is now ignored, just like the organization and role filters.
- 491: PR preview environments are now reliably removed when a PR closes, preview images build on every push regardless of merge conflicts or CI status, previews also build when a draft PR is marked ready for review, and a preview can be rebuilt manually from the Actions UI; the weekly registry cleanup of old preview images is fixed

## 2026-07-20

- 487: login now binds an account to its OIDC subject (`sub`) instead of the email address alone, and rejects a token whose email is already bound to a different `sub`; this prevents account takeover when the token's email claim cannot be fully trusted
- 487: login now requires the OIDC email to be verified (`email_verified`), rejecting the login otherwise
- 487: production now refuses to start unless OIDC_DISCOVERY_URL uses https, protecting OIDC signature validation

## 2026-07-17

- 468: fix the opdracht Updates tab revealing colleague names of planned or ended placements, which the Team tab hides from everyone except the placed colleague and the BM-owner

## 2026-07-15

- 456: fix onboarding wizard's Merken picker rendering broken on pages that don't load the filter/side-panel stylesheets
- 456: fix multiselect dropdown (e.g. Merk in the profile onboarding) being unreachable when the trigger sits low on the screen

## 2026-07-08_3

- 443: add a Veelgestelde vragen (FAQ) page with an accordion, linked from the sidebar footer.
- 443: compact sidebar footer — FAQ, Privacy, Toegankelijkheid and Contact now sit under one "Over Wies" heading
- 450: bump Django to 6.0.7 (security release)
- 449: fix icons/styling occasionally rendering broken after a deploy. fixed by including `Cache-Control: no-store` on HTML responses
- 449: fix edit-pencil (and other inline-edit) icons rendering grey on pages that don't load `side_panel.css`. Moved inline-edit styling to the global `base.css`.

## 2026-07-08_2

- add css comment to trigger styling errors after deploy
- 446: the search field now commits on blur — trimming or clearing the text and clicking away updates the URL/results, without needing Enter or the magnifier

## 2026-07-08

- 438: fix assignment owner link in the assignment side panel so it points back to the page the user is on (instead of the `/assignments/` page)
- 444: staff can reset their own onboarding wizard from the database page (for demos)
- 430: (migration) first-login onboarding wizard — welcome + explanation of the tabs, fill in your profile with labels, and for placed consultants a step to check their own opdracht. Adds `User.onboarding_completed_at` to remember when the wizard was finished or skipped.
- 425: add debug page for request metadata to determine appropriate IP gathering in production
- 439: fix dates showing a capitalized month ("30 Jun 2027") in the "Wie zit waar?"-overzicht ("Tot"-kolom) and the opdracht-zijpaneel teamlijst; they now use the lowercase Dutch abbreviation ("30 jun 2027")

## 2026-07-02

- 402: each filter group now shows its top-3 options plus a "Meer" button that opens a modal with all options (searchable, alphabetical); selected options sort to the top and stay visible even outside the top-3. The modal applies its selection only on "Filter toepassen" (closing without applying discards it), consistent with the opdrachtgever picker
- 402: search now runs on Enter or the magnifier (not on every keystroke) and keeps its text instead of becoming a chip; org suggestions still load live while typing
- 402: added a "Wis alle filters" button next to the active filter chips, so the chips and the clear-all action read together above the results
- 402: fixes — "Toon meer/minder" label now updates; clearing the search no longer leaves a stale term or a missing × button
- 417: remove `ModelBackend` from `AUTHENTICATION_BACKENDS`; `AuthBackend` now inherits from `ModelBackend` so group permissions keep resolving via a single backend, but there is no second password-login path)
- 334: Add privacy declaration and beheer document. The in-product privacy page is regenerated via `manage.py generate_privacy_html`
- 410: fix privacy leak (#383) where non-active plaatsingen were shown to everyone; ended and future (not-yet-started) plaatsingen are now only visible to the placed colleague and the opdracht's Business Manager, each with a privacy note and an "Afgelopen"/"Gepland" chip, consistently across the opdracht team list, the team count, the standalone plaatsing-pagina (`?plaatsing=N`, which was reachable by guessing the URL), the "Wie zit waar?"-overzicht and the profiel-overzicht. The security.txt is now accessible, it was hidden behind the SSO wall.

## 2026-06-24

- 411: (migration) fix assignment updates tab error when there is old unmigrated data
- 413: fix that teammembers on assignment can be removed
- 372: the BM-owner (and support staff in `STAFF_EMAILS`) can delete wies-sourced opdrachten, with a confirmation modal and an audit-trail event; both create and delete now snapshot the rollen (with who filled them) and the opdrachtgevers

## 2026-01-16

- 398: bug fixes — Business Manager link no longer breaks the page and now survives editing/cancelling (#395), only the pencil icon opens inline edit (links and "Toon meer" no longer trigger edit mode), clicking a team member opens the panel via htmx again instead of a full page reload, team period changes now show in updates (#393), no more HiddenInput widget warnings (#389)
- 397: fix team-edit "Neem opdrachtperiode over" checkbox rendering as checked for rows whose effective period differs from the assignment

## 2026-06-11

- 392: support staff (users in `STAFF_EMAILS`) can now edit assignments, even when not owner
- 390: reduce the memory footprint of org sync task to approximately half

## 2026-06-10

- 368: (migration) placement periods can now be set independently from the assignment period via inline-edit on the placement panel; team cards are clickable and open the placement panel
- 368: assignment team form redesigned — separate "Aanvraag toevoegen" and "Geplaatste consultant toevoegen" buttons with progressive field reveal
- 368: lock icon on externally managed fields (e.g. OTYS)
- 368: merge duplicate assignments tool in beheer — preview and confirm UI to combine assignments with the same name, owner, and primary client
- 368: BM can now edit service descriptions (role omschrijving) via inline-edit
- 368: fix that mutliple team members during assignment creation are correctly persisted (became requests before)
- 374: (migration)(remove env vars) remove super users and remove automatic generation during container start
- 331: restore organization breadcrumbs in opdracht side panel; breadcrumb links stay on the page you came from (aanvragen or wie-zit-waar)
- 331: log audit events for changes to the looptijd (start/end date) and team (rollen + plaatsingen) on opdrachten
- 331: restore the ability for placed consultants to edit the opdracht name
- 331: show open rollen (aanvragen) first in the team list again
- 331: fix team-edit silently wiping placement metadata (specific-dates, source_id) on every save by round-tripping Service/Placement PKs through the formset

## 2026-06-01

- 343: remove explicit container name to improve worktrees experience
- 343: remove django admin
- 342: fix "Nieuwe gebruiker" form silently failing on duplicate e-mail — error is now shown inline next to the e-mailveld (regressie van #322)
- 341: Add placement panel: clicking a row in "Wie zit waar?" now shows placement-specific info (role, description, period) instead of the generic colleague profile
- 341: UX improvements for assignment detail panel: text buttons, compact team cards, floating toast on save
- 341: Rename "Vacatures" to "Aanvragen" throughout the UI
- 341: UX improvements for the assignment create form: rename "Diensten" to "Rollen", clarify labels and help text
- 341: Prevent side panel and modals from closing on backdrop click while editing
- 341: Make entire inline-edit row clickable (not just the pencil icon)
- 341: Fix sidebar filter scroll: dynamically adjust max-height for header offset
- 324: replace raw HTML with JRC components across templates and include roos.css
- 324: add sortable Tot column to placement table
- 336: fix user CSV import to accept `;` delimiter and files with UTF-8 BOM
- 336: fix assignment CSV import to accept files with UTF-8 BOM
- 332: fix CSV import collapsing multiple placements onto one Service (e.g. two `Architect` rows on JusticeLink hid one team member); each placed row now gets its own Service, re-uploads stay idempotent
- 332: (migration) split existing CSV-sourced Services that have >1 Placement so each Placement gets its own Service (OTYS-sourced services untouched)
- 320: move /staff content to instellingen
- 320: rename instellingen to beheer
- 320: remove database dump download/upload and 'Sync OTYS' actions
- 320: guard destructive /staff/ actions (clear data, load dummy data) behind the `ENABLE_DESTRUCTIVE_STAFF_ACTIONS` env var
- 320: add usage dashboard for staff members

## 2026-05-11_2

- 322: (migration) deduplicate Colleague and User records and make Colleague and User unique constraint case-insensitive
- 322: fix duplicate Colleague creation on user create/update by reusing an existing unlinked Colleague with the same email (case-insensitive)
- 322: treat email as case-insensitive in user create/update uniqueness checks

## 2026-05-11

- 326: django security update to 6.0.5
- 311: full inline editing on assignments via the new editables system (declarative `EditableSet` per model, single generic HTMX endpoint, reused by full-page forms); row-level permissions in `wies/core/permissions.py`.

## 2026-05-05

- 319: fix user import non-utf8
- 319: fix user import check existence case insensitive
- 304: (migration) register assignment edit events and display on 'Updates' tab
- 304: change dummy data to 50/50 split wies/otys sources
- 304: bump jinja-roos-components to 0.5
- 309: add sidebar footer with links to privacy, toegankelijkheid, contact and GitHub
- 309: add privacy, toegankelijkheid and contact pages
- 309: make sidebar sticky so footer stays visible during scroll
- 58: add logout button to profile and no-access pages
- 58: on logout, clear Django session and redirect to Keycloak's OIDC end_session endpoint
- 58: force credential re-prompt after logout via a session-scoped post_logout cookie + prompt=login, preventing silent re-auth until the browser is closed

## 2026-04-23

- 303: fix that clearing search filter inside client filter re-evaluates list
- 303: fix that clearing org without placements works
- 303: remove inactive tree search code in js
- 280: extend business manager mailto link with pre-filled subject and email body
- 268: add assignment creation form with services, org picker, and inline skill creation
- 268: add success toast notification after assignment creation
- 308: tag preview images per PR commit (pr-N-<sha>) to enable per-commit preview deployments
- 308: add weekly registry GC workflow via snok/container-retention-policy (30-day cut-off, keeps 1 most recent per image, excludes main/latest/release tags)
- 308: show app version on instellingen page
- 308: fix layout overflows (horizontal scrollbar, page height vs header)

## 2026-04-15

- 302: remove migration func and restore ci actions

## 2026-04-13_3

- 299: add func to migrate old data

## 2026-04-13_2

- 273: (squashed migrations) split out rijksauth app

## 2026-04-13

- 279: show historic placements and assignment (only to user themselves and assignment bm)
- 279: introduce editable userprofile
- 279: when colleague has multiple roles on 1 assignment, show on 1 line
- 287: bump zad-actions/deploy to v4
- 281: fix label delete bug introduced in 266
- 282: refactor UI polish, accessibility, and colleague model improvements
- 282: add location icons to assignment cards and colleague panel
- 282: fix XSS, input validation, and accessibility issues
- 282: show service description in team and colleague sidepanels
- 282: redesign placement table columns (Wie, Wat, Waar)
- 282: improve contrast: black links, headings, and icons (WCAG AA)
- 282: add RVO date, textarea, and checkbox widget templates
- 266: (migration) enforce uniqueness on Colleague.email + Colleague.source
- 266: always create Colleague for Users
- 266: (migration) move labels from User to Colleague
- 265: fix opdrachten filter to only consider skills on open services
- 265: make search bar on assignments page same as on wiezitwaar page
- 261: (new env var) move db admin from `/djadmin/db/` to `/staff/`, use SSO login instead of superuser login, access controlled by `STAFF_EMAILS`
- 262: make sidepanels the same between 2 pages
- 262: (migration) change status from assignment to service: (CONCEPT, OPEN, GESLOTEN)
- 251: fix that placement table shows org labels instead of org names
- 251: confirm search by enter press
- 251: add search suggestions: organizations found by abbreviation
- 253: use zad-actions v3
- 245: enable loading initial user via env var (also in production)
- 246: bump htmx to 2.0.8
- 246: bump Python to 3.14
- 246: bump Debian base image to trixie (Debian 13)
- 246: bump ruff to 0.15.6
- 246: bump GitHub Actions: login-action v4, build-push-action v7, setup-node v6
- 246: bump jinja-roos-components (RVO design-tokens 2.2.0, component-library 4.19.0, @nl-rvo/assets 1.0.0)
- 246: remove vendored RVO CSS and npm dependency — now served via jinja-roos-components
- 246: remove Node.js build stage from Dockerfile
- 246: migrate button classes from utrecht-button to rvo-button
- 246: rename color token logoblauw to lintblauw
- 253: persist filter and sort parameters in URL

## 2026-03-17_2

- 247: fix migration that there's only a single primary client
- 283: Implement HTMX for content swap in side panel
- 283: Align 'Toon meer' button with filterbar
- 283: Fix bug opdrachtgever not appearing on 'open opdrachten'
- 283: Show single org in filter when only 1 selected

## 2026-03-17 (invalid, use 2026-03-17_2)

- 221: include business manager assignments in colleague sidepanel
- 221: show period on assignment cards in colleague side panel
- 241: also delete organizationunits from admin db
- 164: introduce actions to automatically deploy on tag and PR
- 192: Add assignments page with organization hierarchy filter, multiselect role filter, and compact card layout
- 192: Support importing OPEN assignments via CSV
- 192: (migration) change VACATURE -> OPEN
- 220: support multiple organizations per assignment
- 220: (migration) add AssignmentOrganizationUnit.role (PRIMARY, INVOLVED)
- 220: make dummy data correct

## 2026-03-06

- add endpoint to worker container for health checks

## 2026-03-05

- 189: Add multi-select checkbox filters
- 189: Add multi-select dropdown in user create/edit modal
- 189: Add reusable multi_select component with search, clear, and keyboard support
- 185: improve docker-compose: remove container names, handle SIGTERM/SIGINT, change to port 8080
- 185: introduce js testing. `just test` runs both, `just test django` / `just test js` run individually
- 185: introduce small starting dataset and add `just load-full-data` for loading large dataset
- 185: (migration) introduce long running tasks through `db_worker` service
- 185: (migration) introduce hierarchial organization structure and synchronization
- bump django to 6.0.3

## 2026-03-03_3

- fix gunicorn, not using control socket

## 2026-03-03_2

- fix startup script not crashing on existing superuser
- fix django container properly waiting for db availability

## 2026-03-03

- 200: switch to PostgreSQL
- 200: run multiple workers in production
- 188: Scaling image on colleague card
- 201: fix pagination

## 2026-02-25

- 199: add db export and import functions for db migration
- 191 and others: bump ruff, gunicorn and cryptography (security)
- 176: Fix that externally managed assignment can not be edited
- 176: Filter out historical placements
- 172: Move dummy_data.json to wies/core/fixtures/
- 149: Change `/plaatsingen/importeren` to `/opdrachten/importeren`
- 149: Change home page from redirect to `/plaatsingen/` to serve placements directly at `/`
- 139: Skip login page, redirect directly to Keycloak (SSO-Rijk)
- 139: Improved "no access" page with context-specific messages based on email domain
- 139: Add `ALLOWED_EMAIL_DOMAINS` setting for ODI email validation
- 139: Add email domain validation to user create, edit and CSV import
- 147: Add security headers (CSP, Permissions-Policy, HSTS, etc.)
- 147: Serve vendor assets (htmx, RVO CSS) locally instead of from CDN
- 143: Bump Django from 5.2.9 to 6.0.1
- 144: Drop django-extensions
- 150: Add Wies logo to navbar item "Wie zit waar?"
- 162: Add pre-commit, ruff, djlint, pytest and coverage report
- 162: Add .editorconfig
- 162: Add GitHub action for labeling pre-commit PRs with label dependencies
- 162: Change formatting according to styling rules
- 161: Fix that BM link no longer resets active filters
- 163: Generalize assignment import to be brand independent
- 177: Refactor app layout: grid-based structure with collapsible sidebar, menubar, mobile responsive
- 177: Refactor base.html to use template includes (menubar, header_logo, filter_sidebar)
- 177: Mobile friendly screens: full-screen overlays for filters, side panel and modals
- 177: Refactor filter JS: extract shared functions to filter_utils.js
- 177: Clean up CSS/JS: CSS custom properties, overlay close registry, extract modals.css
- 177: Add animations to panels and sidebar
- 177: with env var SKIP_OIDC, skip login during development
- 181: Bump django security release

## 2026-01-19

- 136: fix bug with label filters returning wrong answers
- 136: (migration) Change ordering of filters: ministry, client, skill, labels alphabetically, period
- 136: Increase side panel width

## 2026-01-16

- 127: move placement filter in page, with chips
- 127: remove banner, remove jump in sidepanel, wider content
- 132: Update urls & dates from english to dutch
- 135: Styling menu items, adjust Layout, assignment not clickable, back button in side panel
- 133: Add 'Business Manager', change 'Beschrijving' (former 'Extra info') on assignment panel
- 133: (migration) Change assignment.extra_info to max 5000 chars
- 133: Add possibility to edit name and description of assignment by business manager and consultants working on assignment
- 133: Fix ministry and client link from side panel triggering filter

## 2026-01-14

- (backwards incompatible) clean slate - start over with only essential 4W functionality
- Change login to only pass when user is in database
- Remove login requirement from logout endpoint
- Remove possibility to switch off authentication
- Developer is added as user from env vars during setup
- Generalized modal css from filter bar
- Introduce roles (groups) Beheerder, Consultant, Business Development Manager
- Users page with filtering, search, create, edit and delete (only admins)
- Add tests for authentication and user views
- Introduce forms.py/RVOMixin to enable style the form with roos
- Add /users/import csv upload for sourcing starting userlist
- Upgrade to jrc 0.3
- Remove actions menu on assignment
- Introduce "wies" as extra source on records
- Developer user during setup now gets all roles
- Add /placements/import csv upload for sourcing RIG placement list
- Upgrade to django 5.2.9 for security patch
- (migration) Remove hours_per_week on service and placement
- (migration) Make email unique in db
- Fix that RVOMixin uses proper jinja environment (enabling components and other functions)
- 114: Implement right-side panel with colleague and assignment details
- 114: Add support for combining panel & filter URLs
- 114: Remove legacy detail pages
- 114: Add filtering for clients and ministries from panel
- 113: replace brand table with label system for more flexibility
- 113: dedicated admin page for user and label management
- 113: move django admin panel to `/djadmin/`
- 113: fix enter press in user search does not trigger user create
- 113: generalized user_form_modal -> generic_form_modal
- add wies email adress to no-access page
- 102: Add Event model with events 'User.create', 'User.update', 'User.delete', 'Login.success', 'Login.fail'
- 123: Side menu instellingen pagina fully to left
- 123: Styling navigation
- 123: Delete functionality to modal
- 123: Update behaviour gebruikers and labels table rows
- 123: Update showModal behaviour for closing
- 123: Change layout user modal
- 123: Aligned modals
- bump authlib due to path vulnerability

## 2025-10-09

- add period filter to placement page
- add end date of current placement to colleague list
- add availability sorting to colleague list
- (backwards incompatible) change assignment status. new list: LEAD, VACATURE, INGEVULD, AFGEWEZEN
- changed that assignment phase is computed instead of assigned
- changed to also unavailble colleagues are shown when checking out matches
- fix source data to have correct Placement.period_source
- bump authlib dependency due to security patch
- saved note redirects to notes tab, whitespace underneath note form, always show note form
- changed availability timeline: dont show placements outside range
- changed availability timeline: brand and ODI skill filter added to modal, removed client and ministery
- added to availability timeline: start month input
- added search to main navigation
- added search results page
- bump django to 5.2.7 due to CVE (unaffected)
- update clients page
- update page names
- clean up css
- improve query performance
- introduce pagination on placements and colleagues
- remove dashboard page
- move brand filter inside modal
- upgrade rvo token and components to latest
- change tag styling
- introduce "VACATURE" entries in dummy data

## 2025-09-19

- update dependencies to latest, including django security release
- fix that a cancel action on create/edit/remove takes user back to page from which action was perfomed
- add breadcrumbs on client detail page
- add underline active state to main tabs

## 2025-08-21

- add user profile page with RVO tab navigation (Overzicht, Opdrachten, CV, Instellingen)
- link user accounts to colleague profiles via email matching
- add auto-create colleague on login
- add profile edit functionality through existing colleague update form
- add Colleague.email, remove duplicates in dummy data
- add search on assignment "Extra info"
- add possibility to take over hours per week from service
- fix Placement update form dynamic field visibility
- fix RVO mixin to have email and numberfield
- add notes: create and list from assignment detail page
- add possibility for primary action on filter group
- add create assignment button and move organisation into filter modal
- split assignment page into two tabs: services and notes
- nest placement creation under service
- update looks of services/placements
- add link to relevant colleague page for matching

## 2025-08-18

- add dashboard page as landing page with summary cards
- add summary cards to dashboard, clients and assignment detail pages
- add clickable table rows with hover states to all dashboard tables
- add service layer for statistics calculations across all pages
- change environment variables into .env file
- add openidconnect authentication
- update colleague page with RVO design system components and improved layout
- consolidate CSS files - move placement styles to custom.css
- fix Python import statements placed incorrectly within functions
- standardize RVO/Utrecht design system class usage across templates
- fix assignment page filter context and navigation layout
- add service.otys api module
- add syncing between OTYS IIR and wies colleagues

## demo-2025-08-11

- add gunicorn for production server
- add whitenoise for static file serving
- change that you only need container start for production
- add db admin page `/admin/db/`
- change settings into `local` and `production`
- change `production` settings
- change dummy data: remove illogical combination, add more
- add WRITABLE_FOLDER env var for db
- fix static files not found
- remove rvo assets from static files and add as dependency
- add syncing between exact and wies colleagues

## demo-2025-08-04

...
