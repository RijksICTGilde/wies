# Plaatsingspaneel en opdrachtpaneel samenvoegen

Issue: geen nummer (opdracht van Ruben, 28 september 2026, branch `merge-placement-assignment-sheets`). Wie een teamlid, een opdrachtkaartje of een oude `?plaatsing=`-link aanklikt, komt straks altijd in hetzelfde opdrachtpaneel uit, met de rij van die collega uitgelicht en de omschrijving van elke rol direct zichtbaar; het paneel wordt breder (800px).

## Huidige situatie

Drie panelen delen één `nldd-sheet` (`id="side-panel"`, `width="640px"`, vier keer letterlijk in `placements.html`, `assignments.html`, `bezetting.html` en `user_profile.html`). Ze worden gekozen op query-param, in deze volgorde: `?nieuwe-opdracht`, `?plaatsing=`, `?opdracht=` (wint van `?collega=` als beide er staan), `?collega=`. Zes views doen die dispatch elk zelf: `PlacementListView`, `AssignmentListView`, `bezetting`, `user_profile`, plus de POST-handlers die via `HX-Location` terugkeren.

### Wat de panelen tonen

| Onderdeel                                                                                         | Opdrachtpaneel (`?opdracht=`)                                                                        | Plaatsingspaneel (`?plaatsing=`)                                         | Collega-paneel (`?collega=`)                           |
| ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------ |
| Titel                                                                                             | opdrachtnaam (overline "Opdracht")                                                                   | collega-naam                                                             | collega-naam                                           |
| Avatar, e-mail, merk, labels                                                                      | –                                                                                                    | ja                                                                       | ja                                                     |
| Contracturen (BM/beheerder/staff)                                                                 | –                                                                                                    | –                                                                        | ja                                                     |
| Externe bron, omschrijving opdracht, opdrachtgever(s), periode, plaatsingsdatum, business manager | ja, met rijmenu's (org-filter, profiel, e-mailen)                                                    | alleen naam + primaire opdrachtgever, als klikbare rij naar `?opdracht=` | –                                                      |
| Team                                                                                              | volledige lijst: avatar, naam, rol-tag, periode, uren (per rechten), Afgelopen/Gepland-chip, rijmenu | alleen de namen van actieve teamleden, komma-gescheiden                  | –                                                      |
| Periode van déze plaatsing                                                                        | in de teamrij                                                                                        | eigen rij, met chip en privacy-chip; menu "Periode wijzigen"             | –                                                      |
| Rol van déze plaatsing                                                                            | tag in de teamrij; uren als supporting text                                                          | rij "Rol": naam + **omschrijving** · uren; menu "Rol wijzigen"           | –                                                      |
| Andere opdrachten van de collega                                                                  | –                                                                                                    | "Lopende opdrachten" / "Eerdere opdrachten" als kaarten                  | "Opdrachten" als kaarten (actief eerst, dan afgelopen) |
| Tabblad Updates                                                                                   | ja (niet voor OTYS IIR)                                                                              | –                                                                        | –                                                      |
| Bewerken / verwijderen opdracht                                                                   | toolbar (potlood, prullenbak)                                                                        | –                                                                        | –                                                      |
| Teamlid toevoegen/wijzigen/verwijderen                                                            | ja (`?teamlid=`)                                                                                     | –                                                                        | –                                                      |

Het plaatsingspaneel is dus een collega-paneel met één opdrachtblokje erin. Het enige gegeven dat nergens anders staat is de **omschrijving van de rol** (`Service.description`, bijvoorbeeld "Uitvoeren van risicoanalyses en penetratietesten"). De teamrij in het opdrachtpaneel toont alleen de rol-tag. Verder uniek zijn de twee snelbewerkingen ("Rol wijzigen", "Periode wijzigen") via `placement_edit_view`; voor een BM bestaat dezelfde functionaliteit al in "Teamlid wijzigen", voor een geplaatste consultant bestaat "Rol wijzigen" ook al in het rijmenu van het opdrachtpaneel (`assignment_services_row_menu.html`).

De rondgang die het verwarrend maakt: opdrachtpaneel → rijmenu "Bekijk teamlid" → plaatsingspaneel (collega-kop, opdrachtblokje) → rij "Opdracht" → hetzelfde opdrachtpaneel. Drie panelen die er twee zijn.

### Waar het plaatsingspaneel vandaan komt

| Instappunt                                                | Bestand                                                                                      | URL nu                                                                                         |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Persoonskaart op "Wie zit waar?" met precies één opdracht | `PlacementListView._person_cards`                                                            | `?plaatsing=P` (met meer opdrachten: `?collega=C`)                                             |
| Opdrachtkaart in collega-paneel en op de profielpagina    | `_make_assignment_entry` via `_get_colleague_assignments`                                    | `?plaatsing=P` (eerste plaatsing van die collega op die opdracht); BM-opdrachten `?opdracht=A` |
| Rijmenu team, "Bekijk teamlid"                            | `forms/displays/assignment_services_row_menu.html`                                           | `?plaatsing=P`                                                                                 |
| Rijmenu team, eigen rij, "Rol wijzigen" (niet-editor)     | idem                                                                                         | `?plaatsing=P&bewerken=1&veld=skill`                                                           |
| Bezetting                                                 | `bezetting_results.html`                                                                     | rij → `?collega=C`; vandaar de kaarten hierboven                                               |
| Bookmarks, browsergeschiedenis                            | –                                                                                            | `?plaatsing=P`                                                                                 |
| Event-teksten en mails                                    | `services/event_text.py` `Subject`, `_owner_display_context` mailto, flash "Bekijk opdracht" | **nooit** `?plaatsing=`; altijd `?opdracht=` of `?collega=`                                    |

`_resolve_placement_panel` past de zichtbaarheidsregel van #636 toe (`evaluate_placement_visibility`): een afgelopen of geplande plaatsing is voor de geplaatste collega, de BDM-rol en staff; voor anderen is `?plaatsing=P` een 404 (HTMX) of een pagina zonder paneel (volledige load), niet te onderscheiden van "bestaat niet".

### Breedte

- `width="640px"` staat in vier templates; geen CSS-regel verwijst ernaar (`app.css` heeft alleen een `@media (min-width: 641px)` voor het weergave-schakelaartje, los van het paneel).
- NLDD `nldd-sheet` 0.8.82: `width` geldt vanaf de md-breakpoint (641px) en wordt geclampt op `100vw - 2 × 16px`; standaard 360px (md) / 480px (lg, vanaf 1008px). Onder 641px is het altijd een bottom sheet op volle breedte, ongeacht `width`. De sheet is modaal (backdrop, `showModal`), dus de pagina erachter is toch niet bedienbaar zolang hij open staat.
- Bij 640px is de inhoudskolom ongeveer 592px. Wat daar krap is (screenshots van vandaag in de scratchpad, `shots/huidig_*`): de opdrachtgever-breadcrumb wrapt over twee regels; een teamrij met naam + rol-tag + periode + uren + twee chips wrapt zodra de naam of rol wat langer is; met de rol-omschrijving erbij (zie hieronder) is er geen ruimte voor een tweede regel zonder dat elke rij drie regels wordt; de Updates-tab met Van/Naar-blokken; de opdrachtkaarten (`item-width="280px"`) passen net met twee naast elkaar (584px).

## Richtingen

**A. Eén opdrachtpaneel, de collega uitgelicht in de teamlijst (aanbevolen).** Het plaatsingspaneel verdwijnt. Elke teamrij toont voortaan ook de rol-omschrijving. Kom je via een collega binnen (kaartje in collega-paneel of profiel, oude `?plaatsing=`-link), dan staat `?opdracht=A&collega=C` in de URL en zijn de rijen van C gemarkeerd en in beeld gescrold. De persoonsgegevens (e-mail, labels) zitten één klik verderop in het collega-paneel ("Bekijk profiel" in het rijmenu; de terugknop van de paneelstapel brengt je terug).
Nadeel: de uitgelichte rij staat onder de opdrachtgegevens, dus bij een lange omschrijving moet het paneel scrollen om hem te tonen; wie de e-mail van een teamlid zoekt heeft een klik extra.

**B. Opdrachtpaneel met de plaatsing als kopblok.** Via `?plaatsing=` rendert het opdrachtpaneel met bovenaan een blok "Rol van Anke Jacobs" (periode, rol, omschrijving, snelbewerkingen), daaronder de gewone opdrachtgegevens en het team.
Nadeel: het paneel krijgt twee gedaantes afhankelijk van de ingang, dezelfde persoon staat twee keer op het scherm (kopblok én teamrij), en het kopblok is precies het opdrachtblokje van het oude plaatsingspaneel in een andere jas: de verwarring blijft voor de helft bestaan.

**C. Plaatsingspaneel schrappen zonder uitlichting.** Persoonskaarten gaan naar het collega-paneel, opdrachtkaarten naar het opdrachtpaneel, klaar. De rol-omschrijving komt in de teamrij.
Nadeel: vanaf een profiel of collega-paneel land je in een team van tien mensen en moet je jezelf zoeken; een oude `?plaatsing=`-link kan alleen nog naar de opdracht wijzen, niet naar de plaatsing.

Aanbeveling: **A**. Het is C plus een markering, en die markering kost weinig: de rijen komen al uit `visible_service_rows`, dus een verborgen plaatsing wordt vanzelf niet uitgelicht en er is geen nieuwe anti-orakel-logica nodig. De param `collega` bestaat al en wordt al naast `opdracht` geaccepteerd.

## Gebruikersflow

Per instappunt, voor alle rollen tenzij anders vermeld.

**Persoonskaart op "Wie zit waar?"** (weergave Persoon). Precies één opdracht: klik → opdrachtpaneel met de rijen van deze collega uitgelicht (`?opdracht=A&collega=C`), zoals de kaart vandaag het plaatsingspaneel opent. Meer opdrachten: collega-paneel (`?collega=C`), met de opdrachten als kaartjes die elk naar het uitgelichte opdrachtpaneel gaan. E-mail, merk en labels staan in het collega-paneel, vanuit het opdrachtpaneel bereikbaar via "Bekijk profiel" in het rijmenu.

**Opdrachtkaart op "Wie zit waar?"** (weergave Opdracht) en **kaart op Aanvragen**. Ongewijzigd: `?opdracht=A`.

**Teamrij in het opdrachtpaneel.** De rij toont naam, rol-tag, daaronder de omschrijving van de rol, daaronder periode · uren · chips. Een korte omschrijving staat er in zijn geheel; een lange wordt afgekapt met een uitklapper ("Meer") die de rest toont. Waar de grens ligt (aantal regels) is een prototype-keuze. Rijmenu:

- editor (BM-eigenaar, staff): "Teamlid wijzigen" (bestaand), "Bekijk profiel" (nieuw, `?collega=C`), "Uit team verwijderen" (bestaand);
- geplaatste consultant op de eigen rij: "Omschrijving wijzigen" (was "Rol wijzigen"; opent de bestaande plaatsingsbewerksheet als kind van het opdrachtpaneel, `?opdracht=A&teamlid=S`), "Bekijk profiel";
- ieder ander bij een geplaatste rij: alleen "Bekijk profiel";
- aanvraag-rij: ongewijzigd.
  "Bekijk teamlid" vervalt: wat het toonde staat nu in de rij zelf of in het profiel.

**Opdrachtkaart in het collega-paneel of op de profielpagina.** Klik → `?opdracht=A&collega=C`: opdrachtpaneel, rijen van C gemarkeerd, eerste gemarkeerde rij in beeld gescrold. Kaart van een opdracht waar de collega business manager van is: `?opdracht=A`, geen markering (er is geen rij). Lege staat: heeft C op A alleen rijen die deze kijker niet mag zien (afgelopen plaatsing, kijker is buitenstaander), dan is er geen markering en geen melding; de kaart zelf was dan trouwens ook al onzichtbaar.

**Bezetting.** Rij → collega-paneel (ongewijzigd) → kaart → zoals hierboven.

**Directe URL.**

- `?opdracht=A&collega=C`: canoniek. Onbekende of niet-geplaatste C: paneel zonder markering.
- `?plaatsing=P` (bookmark, geschiedenis): alias. De view zoekt de plaatsing op, past `evaluate_placement_visibility` toe zoals nu, en toont bij zichtbaar het opdrachtpaneel met de collega van P uitgelicht. Volledige paginalading: 302 naar de canonieke URL met behoud van filters. HTMX-verzoek: direct de paneelinhoud. Niet zichtbaar of onbekend: 404 (HTMX) / pagina zonder paneel (volledig), precies als nu, zodat een verborgen plaatsing niets prijsgeeft. Een meegegeven `&bewerken=1&veld=…` wordt genegeerd.
- `?opdracht=A` alleen: ongewijzigd.

**Foutpaden.** Onbekende opdracht: bestaande "Niet gevonden"-melding. Team leeg: bestaande "Geen team gevonden.". Omschrijving leeg: de regel ontbreekt gewoon.

## Schermen en visuele keuzes

**Opdrachtpaneel (verandert).** Patroon: het bestaande `assignment_panel_content.html`; de teamrij uit `forms/displays/assignment_services.html`.

- **prototype** — de indeling van de teamrij met drie regels (naam + tag / omschrijving / periode · uren · chips), en de uitklapper voor een lange omschrijving: na hoeveel regels hij begint (één of twee), hoe de knop heet en waar hij staat.
- **prototype** — hoe een uitgelichte rij eruitziet: achtergrondtint plus een niet-alleen-kleur-signaal (een chip "Jij" op de eigen rij, anders een korte visueel verborgen tekst "uitgelicht"), en of er iets in de kop komt te staan (aanbeveling: niets; de terugknop "Anke Jacobs" van de paneelstapel geeft de context al, en bij een directe link moet de markering het alleen doen).
- **prototype** — het rijmenu met "Bekijk profiel" in plaats van "Bekijk teamlid".
- **in de app** — scrollgedrag naar de uitgelichte rij (`block: "center"`, geen animatie bij `prefers-reduced-motion`), gedrag bij twee rijen van dezelfde collega, dark mode van de markering.

**Plaatsingspaneel (verdwijnt).** `placement_panel_content.html` en `_build_placement_panel_data` gaan weg.

**Plaatsingsbewerksheet (verandert).** `placement_edit_panel_content.html` blijft, maar alleen nog voor de geplaatste consultant: kop "Omschrijving wijzigen", rol als alleen-lezen veld, omschrijving bewerkbaar, terugknop naar de opdracht. `veld=period` vervalt (een BM gebruikt "Teamlid wijzigen"). **in de app** — of het formulier op 800px een maximale breedte moet krijgen; NLDD-formulieren van 750px breed lezen slecht. Zo ja: een wrapper met `max-width: var(--primitives-area-640)` op onze eigen container, niet op een `nldd-*`-element.

**Collega-paneel (verandert nauwelijks).** De kaartjes linken naar `?opdracht=A&collega=C`. Geen visuele wijziging.

**Breedte (alle panelen).** **in de app** — 800px via `/vergelijk` naast 720px en 960px, met een opdracht met een lange opdrachtgever-breadcrumb, een team van zes en de Updates-tab. Zie de sectie Breedte voor de onderbouwing van 800.

## Model

Geen wijzigingen. Geen migratie, geen `public_id`-werk (Assignment, Colleague, Placement en Service hebben er al een), niets voor de dummy-data-generator.

## Rechten per rol

Kolommen: Beheerder (groep Beheerder zonder BDM-rol; heeft geen `core.change_assignment`, dus op opdrachten gelijk aan een consultant), Consultant eigen rij (geplaatst op deze opdracht), Consultant overig (niet geplaatst, of andermans rij), BDM niet-eigenaar, BDM-eigenaar (`Assignment.owner` én BDM-rol), Staff (`STAFF_EMAILS`). Alles geldt voor wies-opdrachten; bij een externe bron (`source != "wies"`) is niets bewerkbaar (`_is_wies_sourced`).

| Actie                                              | Beheerder                      | Consultant eigen rij | Consultant overig | BDM niet-eigenaar | BDM-eigenaar | Staff | Regel                                                                                                   |
| -------------------------------------------------- | ------------------------------ | -------------------- | ----------------- | ----------------- | ------------ | ----- | ------------------------------------------------------------------------------------------------------- |
| Opdrachtgegevens en Updates-tab zien               | mag                            | mag                  | mag               | mag               | mag          | mag   | geen regel; elke ingelogde gebruiker (`test_events_partial_accessible_to_unrelated_user`)               |
| Naam en omschrijving opdracht bewerken             | mag niet                       | mag                  | mag niet          | mag niet          | mag          | mag   | `update_assignment_name`, `update_assignment_extra_info` → `_can_edit_assignment_text_field`            |
| Opdrachtgevers, periode, business manager bewerken | mag niet                       | mag niet             | mag niet          | mag niet          | mag          | mag   | geen veldregel → `update_assignment`                                                                    |
| Opdracht verwijderen                               | mag niet                       | mag niet             | mag niet          | mag niet          | mag          | mag   | `delete_assignment`                                                                                     |
| Actieve teamrijen zien                             | mag                            | mag                  | mag               | mag               | mag          | mag   | `evaluate_placement_visibility`, timing `active`                                                        |
| Afgelopen/geplande rij zien (#636)                 | mag niet                       | alleen eigen         | mag niet          | mag               | mag          | mag   | `evaluate_placement_visibility` (`PRIVACY_OWN` / `PRIVACY_BDM`)                                         |
| Uitlichting via `?collega=`                        | alleen zichtbare rijen         | idem                 | idem              | idem              | idem         | idem  | volgt uit `visible_service_rows`; geen eigen regel                                                      |
| Alias `?plaatsing=P`                               | alleen zichtbare P, anders 404 | idem                 | idem              | idem              | idem         | idem  | `evaluate_placement_visibility` in de alias-resolver                                                    |
| Rol-omschrijving op een rij zien                   | mag                            | mag                  | mag               | mag               | mag          | mag   | geen regel (stond al voor iedereen in het plaatsingspaneel)                                             |
| Uren van een geplaatste rij zien                   | mag niet                       | alleen eigen         | mag niet          | mag               | mag          | mag   | `can_view_role_hours` (`roles.py`)                                                                      |
| Uren van een aanvraag zien                         | mag                            | mag                  | mag               | mag               | mag          | mag   | `can_view_role_hours(user, None)`                                                                       |
| Omschrijving van de eigen rol bewerken             | –                              | mag                  | –                 | –                 | mag          | mag   | `update_service_description`                                                                            |
| Rol (skill) en uren van een rij bewerken           | mag niet                       | mag niet             | mag niet          | mag niet          | mag          | mag   | geen veldregel → `update_service` → `update_assignment`                                                 |
| Periode van een plaatsing bewerken                 | mag niet                       | mag niet             | mag niet          | mag niet          | mag          | mag   | `update_placement` → `update_assignment`                                                                |
| Teamlid toevoegen, wijzigen, verwijderen           | mag niet                       | mag niet             | mag niet          | mag niet          | mag          | mag   | `AssignmentEditables.services` zonder veldregel → `update_assignment`; rij via `visible_service_or_404` |
| "Bekijk profiel" (collega-paneel openen)           | mag                            | mag                  | mag               | mag               | mag          | mag   | geen regel; contracturen daar via `read_contract_period`                                                |

Niets in deze tabel is nieuw: de samenvoeging voegt geen recht toe en neemt er geen weg. De enige verschuiving is dat de rol-omschrijving nu in de teamlijst staat in plaats van achter een klik; die was al voor iedereen zichtbaar.

## Breedte

Voorstel: **800px** (`--primitives-area-800`, een NLDD-primitive; tevens `--components-rich-text-wide-max-width`, de bovengrens die het design system zelf aan leesbare tekst stelt).

- Inhoudskolom wordt ongeveer 752px. Daarmee past een teamrij met naam, rol-tag en de meta-regel op één regel voor vrijwel alle namen; de omschrijving krijgt een eigen regel van leesbare lengte; de opdrachtgever-breadcrumb past op één regel; de opdrachtkaarten in het collega-paneel staan ruim met twee naast elkaar (584px nodig).
- 720px (`area-720`) wint te weinig: de meta-regel wrapt nog steeds bij een lange rolnaam. 960px (`area-960`) is breder dan een leesbare regel en laat op een 1280-scherm nog 320px pagina over; de sheet is toch modaal, maar het paneel oogt dan als een pagina in plaats van een paneel.
- Vanaf 1008px (lg): 800px, minstens 208px pagina zichtbaar. Tussen 833 en 1007px (md): 800px, de pagina erachter is nog net zichtbaar (screenshot `huidig_opdracht_*_1000_light.png` laat zien dat 640 daar nu al bijna alles bedekt). Tussen 641 en 832px: NLDD clampt naar `100vw - 32px`, dus vrijwel schermvullend. Tot en met 640px: bottom sheet op volle breedte, ongewijzigd (`huidig_plaatsing_*_390_light.png`).
- Er is geen CSS die aan 640 hangt, dus de wijziging is één attribuut. Om te voorkomen dat het straks weer op vier plekken staat: de sheet in één include `parts/side_panel.html` zetten (de vier `{% block panel %}`-blokken zijn identiek op de modal-mounts in `placements.html` na).
- De kindsheets (opdracht bewerken, teamlid, omschrijving) rekken mee; daar kan een formulier van 750px breed te breed zijn. Beoordelen via `/vergelijk`; zo nodig een max-width op een eigen wrapper.

## Buiten scope

- Het collega-paneel zelf (contractblok, kaartjes, titel "Persoonsgegevens" uit de termen-audit): alleen de links veranderen.
- Een consultant zijn eigen periode laten bewerken: was niet toegestaan en blijft zo.
- Snelbewerking "Periode wijzigen"/"Rol wijzigen" voor een BM per rij: vervalt ten gunste van "Teamlid wijzigen", dat hetzelfde en meer doet (aanname 4).
- Inline bewerken (`inline_edit`) opnieuw in het paneel brengen: bewust vervangen door kindsheets in #427.
- Het Updates-overzicht (branch `event-log`, `plans/event-log.md`): raakt dit paneel niet.
- Toegankelijkheidsfixes van #673 (focus, live region, validatielijsten): die PR gaat voor, zie taak 0.
- Meerdere plaatsingen van één collega op één opdracht samenvoegen tot één rij: beide rijen worden uitgelicht, verder niets.

## Takenlijst

Geen model- of migratiestappen; de volgorde is: voorbereiding, sheet-container, teamrij, uitlichting, rijmenu en bewerksheet, links, alias en opruimen, tests per stap, changelog.

0. **Voorbereiding.** #673 (`a11y-screenreader-fixes`, open sinds 17 september) wijzigt `placement_panel_content.html`, `placement_edit_panel_content.html`, `assignment_panel_content.html` en `colleague_panel_content.html`. Eerst #673 mergen en deze branch rebasen; anders levert het verwijderen van `placement_panel_content.html` een modify/delete-conflict op en moeten de validatielijst-wijzigingen in de bewerksheet met de hand worden overgenomen. Daarnaast staan er in de werkboom ongetrackte bestanden van de branch `event-log` (`wies/core/jinja2/event_log.html`, `parts/event_*.html`, `services/event_text.py`, `tests/test_event_list.py`, `tests/test_event_text.py`); `just test` pakt die tests op en ze horen niet bij deze branch. Eerst opzij zetten (`git stash -u`) of vanuit een schone checkout werken.
1. **Sheet-container en breedte.** Nieuw `parts/side_panel.html` met de `nldd-sheet` (`width="800px"`) en `nldd-page id="side-panel-content"`; de vier `{% block panel %}`-blokken includen het. Test: een templatetest die de vier pagina's rendert en één `nldd-sheet` met dezelfde breedte vindt (naast `test_templates_no_inline_js.py` in `wies/core/tests/`). Screenshots via `/vergelijk` (720/800/960).
2. **Rol-omschrijving in de teamrij.** `forms/displays/assignment_services.html`: tweede supporting-regel met `row.description` (de rij-dicts uit `_services_initial` dragen hem al). Test in `test_placement_views.py` (`AssignmentServicesDisplayVisibilityTest`): omschrijving zichtbaar voor een buitenstaander, uren niet.
3. **Uitlichting `?opdracht=A&collega=C`.** `_build_assignment_panel_data` leest `request.GET.get("collega")`, lost op via `Colleague.public_id` (mis → geen markering, geen 404) en zet `row["highlighted"]` op de rijen van die collega in `team_rows`; template markeert de rij en zet een `data-`hook; `side_panel.js` scrolt de eerste gemarkeerde rij in beeld na `htmx:afterSettle` en bij een server-gerenderde eerste opening. De vier dispatchers hoeven niet te veranderen: `opdracht` wint al van `collega`. Tests (nieuw bestand `test_assignment_panel_highlight.py`, naar het voorbeeld van `PlacementPanelVisibilityTest`): rij gemarkeerd; rij van een verborgen plaatsing niet gemarkeerd voor een buitenstaander, wel voor de collega zelf en voor een BDM; onbekende `collega` → paneel zonder markering; twee rijen van dezelfde collega beide gemarkeerd.
4. **Rijmenu en bewerksheet.** `assignment_services_row_menu.html`: "Bekijk teamlid" → "Bekijk profiel" (`?collega=C`, `hx-push-url="false"` zoals nu); eigen rij "Rol wijzigen" → "Omschrijving wijzigen" met `?opdracht=A&teamlid=S`. `_build_assignment_member_panel_data`: heeft de kijker geen `AssignmentEditables.services`-recht maar wel `update_service_description` op de rij van `teamlid`, dan `_build_placement_edit_panel_data` voor die plaatsing teruggeven (kop "Omschrijving wijzigen", `edit_url` blijft `placement-edit` met `?veld=skill`, `parent_url` zonder `teamlid`). `placement_edit_view`: `fallback` wordt `?opdracht=A&collega=C`; `veld=period` en `PLACEMENT_FIELD_HEADINGS` vervallen. `_page_url_behind_panel`: ook `collega` droppen, anders opent na verwijderen het collega-paneel. Tests: `test_hours.py` (`ServiceHoursPermissionTest`: `test_team_list_offers_the_role_sheet_on_the_own_row_only`, `test_role_form_of_the_consultant_ignores_posted_hours`, `test_placement_panel_role_form_carries_the_hours_for_the_owner_only`), `test_placement_edit.py` (happy path, verboden, 404), `test_inline_edit.py` (`test_row_menu_view_url_uses_public_id` → `?collega=`).
5. **Links omleggen.** `_make_assignment_entry`: `placement_id` → `colleague_public_id`, URL `?opdracht=A&collega=C`. `PlacementListView._person_cards`: bij één opdracht `?opdracht=A&collega=C`, anders `?collega=C`. Tests: `test_placement_weergave.py` (`test_single_assignment_card_links_to_the_placement` wordt "links to the assignment with the colleague highlighted"), `test_placement_views.py` (`ColleagueProfileFutureVisibilityTest`, `ColleagueAssignmentsHistoricalVisibilityTest`: assert op de nieuwe URL).
6. **Alias `?plaatsing=` en opruimen.** `_resolve_placement_panel` wordt `_resolve_placement_alias(request, public_id)`: zelfde lookup en `evaluate_placement_visibility`, zelfde 404/None-gedrag, maar levert `(assignment, colleague)`; de vier dispatchers roepen daarna `_build_assignment_panel_data` aan met de collega als uitlichting, en een volledige paginalading krijgt een 302 naar `_build_panel_url(request, opdracht=…, collega=…)`. Weg: `_build_placement_panel_data`, `placement_panel_content.html`, `other_active_assignments`/`past_assignments`, `assignment_card`. `PANEL_PARAMS` (views en `side_panel.js`) houden `plaatsing` zodat de alias uit een URL gestript blijft worden. Tests: `test_public_id.py` (`PlacementPanelParamTests`: HTMX 200 met de collega gemarkeerd, verborgen → 404, malformed → 404, volledige load verborgen → 200 zonder naam, volledige load zichtbaar → 302 naar canoniek), `test_bezetting.py` (`test_plaatsing_panel_returns_placement_fragment` → opdrachtfragment), `test_placement_panel_500.py` (blijft), `test_placement_views.py` (`PlacementPanelVisibilityTest` en `PlacementPanelPencilPermissionTest` herschrijven tegen het opdrachtpaneel of laten vervallen waar taak 3 en 4 ze dekken).
7. **Toegankelijkheid en beeld.** `wies_a11y.py` op `/?opdracht=A&collega=C` in beide kleurstellingen; screenshots van de teamrij en de kindsheets op 800px; termen-audit: "Details inzet" en de paneeltitel "Plaatsing" verdwijnen vanzelf.
8. **Changelog.** In `CHANGES.md` onder `## unreleased`, één regel per gebruikerszichtbare wijziging: plaatsingspaneel opgegaan in het opdrachtpaneel (omschrijving in de teamrij, lange omschrijving uitklapbaar, collega uitgelicht, `?plaatsing=`-links blijven werken), "Bekijk profiel" in het rijmenu, snelbewerkingen van de BM vervallen ten gunste van "Teamlid wijzigen", paneel 800px breed.

## Tests

Wat bewezen moet worden, met het bestaande bestand dat als voorbeeld dient:

- **Uitlichting** (`test_assignment_panel_highlight.py`, nieuw; voorbeeld `PlacementPanelVisibilityTest` in `test_placement_views.py`): gemarkeerd voor een zichtbare rij; niet gemarkeerd en niet genoemd voor een verborgen rij bij een buitenstaander; wel bij de collega zelf (`PRIVACY_OWN`), een BDM en staff (`PRIVACY_BDM`); onbekende of niet-geplaatste `collega` → 200 zonder markering; BM-opdracht zonder rij → geen markering.
- **Alias** (`PlacementPanelParamTests` in `test_public_id.py`): actief → 200 met collega gemarkeerd; verborgen en onbekend niet te onderscheiden (404); volledige load verborgen blijft 200 zonder naam; volledige load zichtbaar → 302 met filters behouden; `bewerken`/`veld` op de alias genegeerd.
- **Rechten per rol** (`ServiceHoursPermissionTest` in `test_hours.py`, `PlacementEditViewTest` in `test_placement_edit.py`): consultant ziet "Omschrijving wijzigen" alleen op de eigen rij en de sheet bevat geen uren of periode; BDM-eigenaar en staff zien "Teamlid wijzigen"; niet-eigenaar-BDM ziet geen van beide maar wel de uren; buitenstaander ziet omschrijving, geen uren van geplaatste rijen, wel uren van een aanvraag; POST op `placement-edit` blijft geweigerd zonder recht en negeert meegestuurde uren.
- **Links** (`test_placement_weergave.py`, `ColleagueProfileFutureVisibilityTest`): persoonskaart met één opdracht → `?opdracht=…&collega=…`, met meer → `?collega=`; opdrachtkaart van een collega → `?opdracht=…&collega=…` zonder integer-PK; BM-kaart → `?opdracht=` alleen.
- **Rijmenu** (`test_inline_edit.py`): "Bekijk profiel" bouwt `?collega=` met `public_id`; "Bekijk teamlid" en `?plaatsing=` komen niet meer in de rij voor.
- **Sheet-container**: de vier pagina's renderen één `nldd-sheet` met dezelfde breedte.
- **Regressie**: `test_visibility_regressions.py`, `test_assignment_views.py` (`TimelinePlacementPrivacyTests`) en `test_events.py` ongewijzigd groen; querytelling van het opdrachtpaneel niet hoger dan nu (`ServicesInitialQueryCountTest`).

## Open vragen en aannames

Vragen aan Ruben:

1. **Persoonskaart op "Wie zit waar?" met één opdracht.** Aanbeveling: altijd het collega-paneel (`?collega=`), net als bij meer opdrachten; de opdracht is dan één klik verder, met de collega uitgelicht. Alternatief: direct het opdrachtpaneel met de collega uitgelicht, wat sneller is voor "waar zit Anke en met wie", maar de klik op een persoonskaart doet dan iets anders dan bij een persoon met twee opdrachten. Nadeel van de aanbeveling: een klik extra.
2. **Rol-omschrijving op elke teamrij.** Aanbeveling: ja, voor iedereen die de rij ziet (hij stond al voor iedereen in het plaatsingspaneel; dit is de kern van "wie doet wat"). Alternatief: alleen op de uitgelichte rij. Nadeel van de aanbeveling: een team van tien wordt een langer paneel.
3. **Snelbewerking per rij voor de BM.** Aanbeveling: laten vervallen; "Teamlid wijzigen" bevat rol, omschrijving, uren en periode al, en het scheelt een sheet-variant. Alternatief: "Rol wijzigen"/"Periode wijzigen" behouden via de plaatsingssheet met `veld=`. Nadeel van de aanbeveling: twee velden meer in het formulier voor wie alleen de einddatum wil verschuiven.

Aannames zonder vraag:

4. `?plaatsing=P` blijft onbeperkt werken als alias; hij kost één functie en voorkomt dode bookmarks. Nieuwe links gebruiken hem nooit meer.
5. Canonieke URL voor een uitgelichte collega is `?opdracht=A&collega=C`, niet `?opdracht=A&plaatsing=P`: alle rijen van de collega worden uitgelicht, de zichtbaarheidsfilter van de teamlijst geldt automatisch, en de param bestaat al.
6. Een volledige paginalading op de alias redirect (302) naar de canonieke URL; een HTMX-verzoek rendert direct zonder URL-correctie (de paneelstapel in `side_panel.js` pusht de aangevraagde URL zelf; een oude URL in de stapel is onschadelijk).
7. Het collega-paneel wordt inhoudelijk niet aangepast; de "Team"-regel (namen) en "Lopende/Eerdere opdrachten" uit het plaatsingspaneel vervallen zonder vervanging, want het opdrachtpaneel en het collega-paneel tonen dat al.
8. Geplaatste consultants mogen nog steeds alleen de omschrijving van hun eigen rol wijzigen; de kop van de sheet wordt "Omschrijving wijzigen" in plaats van "Rol bewerken", omdat de rol daar alleen-lezen is.
9. De breedte is voor alle panelen gelijk (één sheet); geen aparte breedte per paneeltype.
10. #673 landt vóór deze branch. Gebeurt dat niet, dan worden de hunks van #673 op `placement_edit_panel_content.html` (validatielijsten, `novalidate`, banner voor non-field errors) hier overgenomen en die op `placement_panel_content.html` laten vallen.
11. Geen wijziging aan events: plaatsingsbewerkingen blijven als "Team"-event op de opdracht gespiegeld (`PlacementEditables.audit_mirror`).

## Verloop

- **Plan goedgekeurd door Ruben (28 september 2026)** met drie beslissingen. Vraag 1: een persoonskaart met één opdracht opent direct het opdrachtpaneel met de collega uitgelicht, niet het collega-paneel; dat is het huidige gedrag van die kaart en het snelste antwoord op "waar zit deze persoon". Vraag 2: de rol-omschrijving komt op elke teamrij, maar een lange omschrijving gaat achter een uitklapper, zodat een groot team het paneel niet volschrijft. Vraag 3: de snelbewerkingen "Rol wijzigen" en "Periode wijzigen" voor de BM vervallen; "Teamlid wijzigen" dekt ze.
- **/vergelijk in de app in plaats van de canvas (28 september 2026).** Breedte: 800px gekozen boven 720 (opdrachtgever en teamrij wrappen nog) en 960 (regels te lang). Omschrijving: één regel, daaronder de NLDD-knop "Toon meer" met pijltje, dezelfde als bij de opdrachtomschrijving; twee regels (rij te hoog) en een klein tekstlinkje "meer" (valt weg aan het eind van de regel, en NLDD heeft geen apart uitklapcomponent) zijn afgevallen. Uitlichting: alleen een tint, de balk links erbij was te druk. Beelden in ~/Downloads/wies-vergelijk-paneel/.
- **Bouw (28 september 2026).** Gebouwd volgens richting A. Afwijkingen van de takenlijst: PR #673 stond nog open en conflicteerde al met main, dus is aanname 10 gevolgd (deze branch eerst; de #673-hunks op de bewerksheet komen mee bij een rebase). De alias `?plaatsing=` redirect bij een volledige lading naar `?opdracht=&collega=` met behoud van filters; een htmx-verzoek rendert direct. Na het verwijderen van een opdracht valt ook `collega` uit de URL, anders opent het collegapaneel over de lijst. De consultant-sheet heet "Omschrijving wijzigen" en de terugknop noemt de opdracht. De ongetrackte event-log-bestanden zijn blijven staan; hun tests draaien niet mee (`--ignore`).
- **Review en toegankelijkheid (28 september 2026).** Reviewer: blocker (de #576-regels voor "Toon meer" waren bij het opruimen van de varianten verdwenen) hersteld; `color="blue"` op de chip bestond niet. Toegankelijkheid: de tint alleen was geen zichtbaar signaal (1.4.1), en na "Bekijk profiel" landt de focus midden in het collegapaneel (2.4.3, ouder dan deze branch). Ruben vond de tint op een vastzittende hover lijken en wilde "Toon meer" kleiner: de knop is nu `size="xs"`, en de uitlichting is op zijn verzoek helemaal weggehaald om te zien of scrollen naar de rij alleen genoeg is. `?collega=` blijft de rij in beeld scrollen; geen tint, balk of chip. Wordt bekeken in de app vóór de beslissing.
- **Beslissingen na de review (28 september 2026).** Ruben: geen uitlichting, ook geen chip "Jij"; de scroll naar de rij is het enige spoor van `?collega=`. Omschrijving: twee regels (afkap op 180 tekens), periode-regel erboven, "Toon meer" op maat `xs` inline achter de afkap. De chip "Gepland" (sinds #410) gaat weg op teamrij en opdrachtkaart; de datums zeggen het al, het oogje blijft. Reviewpunten: "Omschrijving wijzigen" houdt `collega` in de URL zodat Opslaan op de rij landt; de htmx-alias negeert `bewerken`/`veld` (test); `aria-expanded` op "Toon meer"; drie docstrings bijgewerkt; de POST-only takken van de bewerksheet blijven met een docstring die dat zegt. Toegankelijkheid: een paneel landt de toetsenbordfocus op zijn titel als niets in het nieuwe paneel matcht (focus_restore.js, `#panel-title[tabindex=-1]`); de scroll-focus op de rij is niet gedaan, omdat een focusring op de rij weer als uitlichting zou ogen. Blijft liggen: icoon "user" vs "person" (beide geldig, "user" is wat het opdrachtpaneel al gebruikt); de open vraag over een rol met twee plaatsingen (oude link toont dan alleen de nieuwste rij) ligt bij Ruben.
- **Bekende beperking (Ruben, 28 september 2026).** Een rol die opnieuw is ingevuld heeft twee plaatsingen; de teamlijst toont per rol alleen de nieuwste. Een oude `?plaatsing=`-link naar de vervangen plaatsing opent nu het opdrachtpaneel zonder rij van die collega, waar het oude paneel de plaatsing zelf toonde. Komt voor in de data, geaccepteerd: de afgelopen plaatsing staat nog op het collegapaneel onder de eerdere opdrachten, en nieuwe links wijzen nergens meer naar een plaatsing.
