<!--
  Source of truth for this handbook page, also shown in Wies at /handboek/.
  After editing, regenerate the in-product pages:
      uv run python manage.py generate_docs_html
-->

# Samenwerken

## Zo werken we

We werken in korte iteraties en valideren continu met gebruikers: liever een kleine stap die we laten zien en bijsturen, dan lang bouwen in het donker.

Elke wijziging gaat via een branch en een PR naar `main`, en we werken met het vier-ogenprincipe: niets komt in `main` zonder dat een tweede ontwikkelaar het heeft nagekeken en goedgekeurd. Elke merge op `main` wordt automatisch gebouwd en uitgerold naar de main-omgeving (main-deploy.yml); productie krijgt een release met een datum-tag.

### Van idee tot merge

1. Maak een branch vanaf een actuele `main`. Pre-commit weigert een commit direct op `main`.
2. Bouw de wijziging met tests. Commitberichten zijn Engels en noemen het issuenummer waar dat kan.
3. Is de wijziging zichtbaar voor gebruikers? Voeg een regel toe in `CHANGES.md` onder `## unreleased`, in het Engels: `- <PR#>: <beschrijving>`. Het PR-nummer weet je pas na het openen; vul het dan in.
4. Draai `just test` en `just pre-commit` tot ze groen zijn.
5. Open de PR. CI draait de Django- en JS-tests en een Trivy-scan, en zet een preview-omgeving op (`pr-preview.yml`) waar de reviewer de wijziging in het echt kan bekijken.
6. Een tweede ontwikkelaar reviewt en keurt goed. Pas dan merge je; de preview wordt opgeruimd.

### Zo reviewen we

Dit is het vier-ogenprincipe in de praktijk: elke PR wordt nagekeken door een tweede ontwikkelaar. Een goede review:

- Groepeert opmerkingen per thema (bijvoorbeeld UX, datamodel, performance, tests) en maakt onderscheid tussen een open vraag en een concrete suggestie.
- Houdt het relevant: wat de feature tegenhoudt, staat voorop. Een goed idee dat buiten de scope valt, wordt een nieuw issue in plaats van een extra ronde.
- Legt per punt de conclusie vast, zodat later terug te lezen is waarom iets zo is gebouwd. Grotere keuzes horen in een PDR in `PDR/`.

### Een modelwijziging

1. Pas het model aan in `wies/core/models.py`. Nederlandse veldlabels via `verbose_name`; een ForeignKey krijgt een `related_name`.
2. Komt het model ooit in een URL? Geef het een `public_id` (zie [Modellen](de-code.md#modellen)).
3. Werk de dummydata bij in `wies/core/management/commands/load_full_data.py`. Beide profielen (`base` en `full`) lopen door dezelfde `generate()`.
4. Genereer de migratie: `just manage makemigrations`. Een migratie importeert niets uit de app.
5. Werk formulieren, Editables en views bij.
6. Draai de tests; `test_migrations.py` vangt een vergeten migratie.

### Een NLDD-upgrade

Dependabot opent de PR. Lees de changelog van het designsysteem op breaking changes vóór je merget: hernoemde attributen en tokens vallen stil terug op een standaard. Klik daarna de belangrijkste schermen door, in licht én donker.

### Een release

1. Maak een releasebranch vanaf `main`.
2. Zet in `CHANGES.md` de datum op de plaats van `unreleased` en open een nieuwe `## unreleased`.
3. Merge de releasebranch in `main`.
4. Tag met de datum, bv. `git tag -a 2026-01-19 -m "2026-01-19"`, en push de tag. CI bouwt het image en rolt uit naar productie.
5. Voer eventuele post-release-acties uit; die staan in de PR-beschrijvingen.

### Taal

Code, commits, changelog en PR-titels zijn Engels. Alles wat de gebruiker ziet is Nederlands, in de je-vorm en op B1-niveau, met dezelfde woorden als in de woordenlijst in [Wies in het kort](aan-de-slag.md#wies-in-het-kort).

## Testen

Een PR is pas klaar als `just test` en `just pre-commit` groen zijn, lokaal én in CI. Zelf groen krijgen kost minuten; een rode CI kost de reviewer een ronde.

### Tests schrijven

- Tests staan in `wies/core/tests/`, één bestand per feature (`test_<feature>.py`), plus `wies/rijksauth/tests/` en `wies/startpage/tests/`.
- Gebruik Django's `TestCase`. Maak testdata inline met ORM-aanroepen; er zijn geen factories en geen fixtures, op één XML-bestand met organisaties na.
- Log in met `self.client.force_login(user)`. Rollen geef je met de helpers in `tests/role_helpers.py`: `grant_business_manager()`, `grant_consultant()`, `make_staff_user()`, samen met `@override_settings(STAFF_EMAILS=...)`.
- Test een view voor **elke rol**: mag het voor de ene rol, en wordt het geweigerd voor de andere?
- Inline edits test je met `post_inline_edit()` uit `tests/inline_edit_helpers.py`.
- Een enkel bestand draaien: `just manage test wies.core.tests.test_roles`.

### Wat de bewakers vangen

| Bewaker                          | Vangt                                                             | Waar                     |
| -------------------------------- | ----------------------------------------------------------------- | ------------------------ |
| `test_migrations.py`             | Een modelwijziging zonder migratie                                | Tests                    |
| `test_templates_no_inline_js.py` | Inline JavaScript in templates                                    | Tests                    |
| `test_role_matrix.py`            | Een rollenmatrix die afwijkt van de regels                        | Tests                    |
| Ruff (lint + format)             | Stijl, bugs, beveiliging (bandit), Django-regels; regellengte 120 | Pre-commit, CI           |
| djLint, prettier                 | Opmaak van templates, JS, CSS en YAML                             | Pre-commit               |
| `no-commit-to-branch`            | Een commit direct op `main`                                       | Pre-commit               |
| `detect-private-key`             | Een sleutel die per ongeluk mee wil                               | Pre-commit               |
| Trivy                            | Kwetsbaarheden in afhankelijkheden en het image                   | CI (`security-scan.yml`) |

### Datamigraties testen

Tests voor een datamigratie (zoals `test_public_id_migration.py`) gebruiken `MigrationExecutor`: migreer naar het punt vóór je migratie, zet data klaar via de historische modellen, migreer verder en controleer. Zet de database in `tearDown` terug naar het **laatste blad** van de migratiegrafiek, nooit naar een vaste naam. Een vaste naam draait stil alle latere migraties terug, en de rest van de testsuite draait dan op een oud schema.

### Een `# noqa` is een uitzondering

Ruff staat breed aan. Moet een regel echt worden onderdrukt, schrijf er dan bij welke regel het is en waarom het hier terecht is, bijvoorbeeld: `# noqa: PLC0415 (import not at top level) — Django signal registration must happen inside ready()`.

## Valkuilen

De meeste fouten in Wies falen **stil**: geen foutmelding, alleen iets wat niet werkt.

| Valkuil                                                                     | Hoe je het merkt                                                                                                      | Wat je doet                                                                                                 |
| --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Inline JavaScript in een template                                           | Knop doet niets; alleen een CSP-waarschuwing in de console                                                            | `data-action` + `ui_handlers.js` (zie [Templates](de-code.md#templates))                                    |
| `show()` op een sheet of modal die net is ingeswapt                         | Venster gaat niet open, geen fout                                                                                     | Eerst `await el.updateComplete`, of `data-auto-show` gebruiken (`dialog.js`)                                |
| `href` én `hx-get` op een `nldd-list-item`, `nldd-card` of `nldd-menu-item` | Browser navigeert weg, de htmx-respons verdwijnt                                                                      | Kies één van de twee, of laat `hx_link_guard.js` het afvangen                                               |
| POST vanuit een menu-item in een shadow root                                | Je kunt er geen `<form>` omheen zetten                                                                                | POST vanuit JS met het CSRF-token uit de markup (`menu_nav.js`)                                             |
| Eigen widget zonder `wire_field_errors`                                     | Validatiefout is onzichtbaar, ook voor screenreaders                                                                  | `wire_field_errors(field)` in het widget-template                                                           |
| `<form>` zonder `novalidate`                                                | Browser houdt de inzending tegen zonder melding                                                                       | Elk formulier draagt `novalidate`; de server oordeelt                                                       |
| Geraden icoonnaam of `appearance`                                           | Icoon rendert niet, of standaardstijl                                                                                 | Opzoeken in `custom-elements.json` of de storybook (`edit` heet `pencil`, `lock` heet `lock-closed`)        |
| Niet-bestaand CSS-token                                                     | Ziet er goed uit in licht, kapot in donker                                                                            | Altijd in beide modi testen                                                                                 |
| Integer-pk in een URL                                                       | Iedereen kan records aftellen                                                                                         | `public_id` en `<uuid:public_id>` (zie [Modellen](de-code.md#modellen))                                     |
| Eén `AddField` met `default=uuid.uuid4`                                     | Alle bestaande rijen krijgen dezelfde UUID, unique-constraint faalt                                                   | Migratie in drie stappen (zie [Modellen](de-code.md#modellen))                                              |
| App-code importeren in een migratie                                         | Migratie breekt zodra de app-code verandert                                                                           | Alles uitschrijven in de migratie; stdlib-defaults                                                          |
| `specific_start_date` direct lezen                                          | Verkeerde datum als de periode van de opdracht komt                                                                   | `start_date`, of `annotate_placement_dates()` in lijsten                                                    |
| `period_source` vergelijken                                                 | Plaatsing kent `SERVICE`/`PLACEMENT`, rol kent `ASSIGNMENT`/`SERVICE`                                                 | Controleer per model welke waarden het kent                                                                 |
| Matchen op een rol-label                                                    | Breekt bij een hernoeming                                                                                             | Match op de sleutel (`business_manager`), toon met `role_label()`                                           |
| Een regel buiten `permissions.py`                                           | Wordt nooit geregistreerd                                                                                             | Regels alleen in `permissions.py`                                                                           |
| "Dienst" of "service" in UI-tekst                                           | Inconsistente app                                                                                                     | De app zegt **rol**; zie de woordenlijst in [Wies in het kort](aan-de-slag.md#wies-in-het-kort)             |
| OTYS-opdracht bewerken                                                      | Geen potlood, ook niet als BM                                                                                         | Klopt: `WIES_SOURCED` maakt geïmporteerde data alleen-lezen                                                 |
| `wies/core/static/vendor/` ontbreekt                                        | Pagina zonder opmaak, 404 op `nldd.min.js`                                                                            | `just vendor` (of `just up`, dat het ook doet)                                                              |
| Testen in een git worktree                                                  | Tests zijn groen, maar draaiden op de verkeerde code: een extra -v op docker compose run verliest van de mount .:/app | Draai pytest buiten Docker in de worktree, en controleer het aantal tests                                   |
| `features/inline-editing.md` letterlijk volgen                              | Klassen bestaan niet meer                                                                                             | De code wint; zie de noot bij [Editables](de-code.md#editables)                                             |
| `services/urls.py` en `errors.py`                                           | Geen URLconf en geen error-views                                                                                      | URL-helpers en exceptieklassen; routes staan in `config/urls.py`, error-views in `views.py`                 |
| pytest met config.settings.local                                            | Gesimuleerde fouten uit de tests komen in het Mattermost-kanaal; met SKIP_OIDC aan falen tientallen redirect-tests    | Altijd config.settings.test (dat doet pytest standaard); MATTERMOST_*-variabelen en SKIP_OIDC niet meegeven |

## Oefenopdrachten

Lezen is leuk, doen blijft beter hangen. Pak een eigen branch die je na afloop weggooit, en ga je gang.

### Rondkijken

- Open http://localhost:8080 en klik een opdracht aan. Zoek in `config/urls.py` en `views.py` welke view het zijpaneel bouwt, en welk template in `parts/` erin komt.
- Open hetzelfde paneel door de URL met `?opdracht=<uuid>` direct in een nieuw tabblad te plakken. Waarom gaat het paneel nu ook open, zonder htmx?
- Open de Network-tab van je browser en klik op een kaart. Welke headers stuurt htmx mee, en welke daarvan leest de view?
- Bekijk `/beheer/rollen/`. Zoek in `permissions.py` de regel achter één vinkje in die matrix.

### Rechten

- Log in als consultant (haal je eigen rollen weg in Beheer › Gebruikers en zet ze daarna terug met just manage ensure_initial_user, dat leest `INITIAL_USER_EMAIL`). Wat zie je niet meer?
- Schrijf een test die bewijst dat een consultant een opdracht niet mag verwijderen en een business manager wel. Gebruik `role_helpers.py`.

### Bouwen

- Voeg aan `Assignment` een tekstveld toe (bijvoorbeeld een interne notitie). Doorloop de hele modelchecklist: migratie, dummydata, `Editable`, het bewerk-sheet, een test.
- Bekijk hoe de bestaande actie toggle-long-text werkt. Voeg dan een eigen knop toe, bijvoorbeeld een die een tekst naar het klembord kopieert, met `data-action` en een nieuwe entry in `CLICK_ACTIONS`. Controleer dat `test_templates_no_inline_js.py` groen blijft. Zet daarna expres een `onclick=` in je template en kijk wat er in de browser gebeurt.
- Gebruik een icoon dat niet bestaat (`icon="potlood"`). Wat zie je? Zoek de juiste naam op in `custom-elements.json`.

### Afronden

- Draai `just test` en `just pre-commit` tot alles groen is.
- Schrijf een changelogregel voor je notitieveld, zoals hij in `CHANGES.md` zou staan.
- Bespreek je branch met een collega alsof het een echte PR is.

## Verder lezen

In de repo, in deze volgorde:

| Document                                                 | Waarover                                                                     |
| -------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `README.md`                                              | Installatie, commando's, releaseproces                                       |
| `docs/roles.md`                                          | Rollen en rechten in detail, met herstel na een lockout                      |
| `features/public_id.md`                                  | UUID's in URL's en de migratie in drie stappen                               |
| `features/inline-editing.md`                             | Het Editables-systeem (let op de noot bij [Editables](de-code.md#editables)) |
| `wies/rijksauth/README.md`                               | Inloggen via OIDC en het `User`-model                                        |
| `.claude/rules/nldd-integration.md`                      | De valkuilen van webcomponenten in een server-gerenderde app                 |
| `.claude/rules/code-style.md`, `models.md`, `testing.md` | Conventies voor code, modellen en tests                                      |
| `docs/privacy.md`, `SECURITY.md`                         | Privacyverklaring en beveiligingsbeleid; ook in de app zichtbaar             |
| `PDR/`                                                   | Productbesluiten en hun onderbouwing                                         |

Buiten de repo:

- [NLDD-designsysteem](https://design.digitaledienst.overheid.nl/): richtlijnen en componenten
- [NLDD storybook](https://minbzk.github.io/storybook/): alle componenten met voorbeelden
- [@nldd/design-system op npm](https://www.npmjs.com/package/@nldd/design-system)
- [htmx-documentatie](https://htmx.org/docs/)
- [Django-documentatie](https://docs.djangoproject.com/)
- [Jinja2-documentatie](https://jinja.palletsprojects.com/)
