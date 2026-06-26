# Review Checklist (intern — niet committen)

Werklijst die we zelf gebruiken bij het reviewen van PR's in Wies.
Niet uitputtend; gebruik je oordeel en schaal mee met de grootte van de PR.

## Correctheid & gedrag

- Doet de code wat de PR/issue belooft? Eén PR = één ding (geen scope-creep).
- Edge-cases gedekt: leeg, `None`, legacy/niet-gemigreerde data, dubbele acties, race conditions.
- Backwards-compatibility met bestaande data (bv. oude audit-events, oude fixtures).
- Migraties: reversibel waar mogelijk; bij lossy migratie bewust en gedocumenteerd; getest.

## Tests

- Testen ze het echte gedrag, niet alleen happy-path? Falen ze zónder de fix?
- Testdata inline aangemaakt, niet via fixtures (projectregel).
- Views getest met ingelogde users; permissies per rol (Beheerder/Consultant/BDM); form-validatie.
- `just test` groen.

## Security & privacy (overheidscontext — zwaar wegen)

- Permission-checks aanwezig (`has_permission` / `user_can_edit_*`); querysets gefilterd op rechten → geen datalek.
- Geen gevoelige data in logs. Input gevalideerd via forms. OIDC niet omzeild.
- Geen credentials/secrets in code.
- AVG: wordt persoons-/auditdata correct bewaard of bewust verwijderd? Is verwijderen van auditinformatie akkoord?
- Geen nieuwe injectie-/escaping-risico's (Jinja2 auto-escape niet doorbroken).

## Projectconventies (Wies-specifiek)

- Modelwijziging → `load_full_data.py` + `base_dummy_data.json` + migratie + forms/views bijgewerkt (model-workflow).
- Nieuw bewerkbaar veld → als `Editable` in `editables/`, niet als bespoke form-field.
- UI: jinja-roos-components + RVO-classes, Nederlandse labels, `rvo-icon-*` opgezocht (niet geraden), WCAG/toegankelijkheid.
- `timezone.now()` i.p.v. `datetime.now()`; type hints op publieke functies; `ruff check`/`format` schoon.

## Administratieve taken

- **Changelog**: entry onder `## unreleased` in `CHANGES.md`, formaat `- <PR#>: <omschrijving>` — PR-nummer klopt en omschrijving dekt de lading.
- Issue gekoppeld: PR sluit het juiste issue (`closes #...`) en het issue dekt wat er daadwerkelijk gebeurt.
- PR-titel & -omschrijving kloppen en zijn begrijpelijk; geen Claude/AI-/tool-verwijzingen in titel, body of commits.
- Migratiebestanden: oplopende nummering zonder gat/conflict; afhankelijkheid wijst naar de juiste vorige migratie; één migratiekop per logische wijziging.
- Branch is up-to-date met `main`; geen ongerelateerde bestanden/debug-output/commented-out code meegecommit.
- Documentatie/skills/rules bijgewerkt als gedrag of conventies wijzigen.
- Geen achtergebleven `TODO`/`FIXME`/`print()`/`console.log` die niet bedoeld zijn.

## DRY / KISS / structuur

- Geen duplicatie van bestaande logica; hergebruik wat er al is.
- Eenvoudigste oplossing die werkt; geen onnodige abstractie of belt-and-suspenders zonder reden.
- Zit de code op de juiste plek volgens de projectopzet (models/views/forms/querysets/editables/services)?

## Onderhoudbaarheid & stijl

- Foutafhandeling: smal vangen (specifieke excepties) i.p.v. bare `except`; nuttige logging mét context (id/veld).
- Naamgeving helder (NL UI / EN code); geen dode code.
- Comments leggen _waarom_ uit, niet _wat_; kort en zelf-verklarend; geen historische/PR-verwijzingen in code.
- Niet te veel comments — comment moet waarde toevoegen of weg.

## Performance

- N+1 queries vermijden (`select_related`/`prefetch_related`).
- Migraties/loops over grote tabellen: bewust en acceptabel.
