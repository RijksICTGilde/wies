# Migratieplan: RVO naar NLDD Design System

## Overzicht

Volledige migratie van de Wies-applicatie van RVO/JRC design system naar NLDD (@nldd/design-system) web components. De bestaande NDD POC (`/ndd/` routes) wordt de basis.

## Huidige staat

- **RVO stack** (productie, `/`): 89 RVO CSS classes, 15 Utrecht classes, 25 JRC `<c-*>` component tags
- **NDD POC** (`/ndd/`): Werkende parallelle stack voor alle hoofdpagina's
- **Ontbrekend in POC**: assignment_create, error pages, contact/privacy/toegankelijkheid, staff dashboard/database, organization admin, inline editing, form widget layer

## Strategie

NDD POC templates promoveren naar de hoofdroutes. Ontbrekende templates aanvullen. RVO artefacten verwijderen.

---

## Fase 0: Form-infrastructuur (Complexiteit: Medium)

**Doel**: NDD form templates maken zodat forms geen RVO markup meer produceren.

### 0a: NDD form templates + mixin

**Aanpak**: Forms moeten native HTML inputs renderen (geen NDD web components) — dit vermijdt Shadow DOM problemen met HTMX en Django form handling.

- `wies/core/form_mixins.py` — Voeg `NlddFormMixin` toe naast `RvoFormMixin`
  - `template_name = "nldd/forms/form.html"`
  - `field.template_name = "nldd/forms/field.html"`
  - Widget templates wijzen naar `nldd/forms/widgets/*.html`
- Maak `wies/core/jinja2/nldd/forms/` directory met:
  - `form.html` — form wrapper met NLDD spacing
  - `field.html` — field wrapper (label + input + errors)
  - `errors/list/default.html` — error list
  - `widgets/text.html`, `email.html`, `select.html`, `textarea.html`, `date.html`, `checkbox.html`, `radio.html`, `checkbox_select.html`, `multiselect.html`
- `wies/core/widgets.py` — Maak template_name configureerbaar in `MultiselectDropdown` en `OrgPickerWidget`
- Maak `wies/core/jinja2/nldd/widgets/org_picker.html`

### 0b: Inline edit NDD templates

- Maak `wies/core/jinja2/nldd/parts/inline_edit/display.html` — vervang `rvo-alert`, `rvo-icon-bewerken` met NDD equivalenten
- Maak `nldd/parts/inline_edit/form.html` — vervang `<c-button>`, `rvo-form-field` met `<ndd-button>`, NDD classes
- Maak `nldd/parts/inline_edit/collection_form.html`
- Maak NDD display templates: `nldd/forms/displays/assignment_owner.html`, `assignment_period.html`, `assignment_services.html`, `colleague_labels.html`, `organizations.html`, `textarea.html`

### Verificatie

- Unit tests: NDD forms renderen zonder `rvo-` classes
- Bestaande RVO tests blijven groen

---

## Fase 1: Ontbrekende NDD templates (Complexiteit: Medium-Hoog)

**Doel**: Elke pagina heeft een NDD equivalent.

### 1a: Ontbrekende pagina templates

| Pagina                        | Nieuw NDD template                          |
| ----------------------------- | ------------------------------------------- |
| Assignment create             | `ndd/assignment_create.html`                |
| Error pages (400/403/404/500) | `ndd/base_error.html` + `ndd/400.html` etc. |
| Contact                       | `ndd/contact.html`                          |
| Privacy                       | `ndd/privacy.html`                          |
| Toegankelijkheid              | `ndd/toegankelijkheid.html`                 |
| No Access                     | `ndd/no_access.html`                        |
| Staff dashboard               | `ndd/staff_dashboard.html`                  |
| Staff database                | `ndd/staff_database.html`                   |
| Organization admin            | `ndd/organization_admin.html`               |
| User import                   | `ndd/user_import.html`                      |

### 1b: Ontbrekende partial templates

- `ndd/parts/assignment_events_timeline.html`
- `ndd/parts/assignment_org_modal.html`
- `ndd/parts/assignment_services_form.html`
- `ndd/parts/service_row.html`
- `ndd/parts/colleague_assignment_cards.html`
- `ndd/parts/task_list.html`
- `ndd/parts/flash_messages.html`
- `ndd/parts/footer_sidebar.html`
- `ndd/parts/search_suggestions.html`
- `ndd/parts/label_category.html`

### 1c: NDD routes en views

- `config/urls.py` — Voeg `/ndd/` routes toe voor alle nieuwe pagina's
- `wies/core/views.py` — Voeg NDD view variants toe

### Verificatie

- Extend `NDDViewRendersTest` voor alle nieuwe pagina's
- `NDDIsolationTest` verifieert geen RVO classes in NDD templates
- Volledige test suite groen

---

## Fase 2: JavaScript migratie (Complexiteit: Medium)

**Doel**: Alle JS werkt met NDD markup.

### 2a: NDD-compatible JS

| Huidig bestand               | Actie                                                   |
| ---------------------------- | ------------------------------------------------------- |
| `js/inline_edit.js`          | Maak `js/ndd/inline_edit.js` — NDD toast markup         |
| `js/assignment_form.js`      | Maak `js/ndd/assignment_form.js` — NDD button classes   |
| `js/assignment_org_tree.js`  | Maak `js/ndd/assignment_org_tree.js` — NDD radio/button |
| `js/side_panel.js`           | Bestaat al als `js/ndd/side_panel.js`                   |
| `js/filters/multi_select.js` | Vervang `.rvo-text` selector met data-attribuut         |
| `js/filters/filters.js`      | Vervang `.rvo-form` selector met data-attribuut         |

### 2b: Gedeelde JS design-system-neutraal maken

Waar mogelijk: query op data-attributen/IDs ipv design-system classes.

### Verificatie

- JS test suite groen
- Handmatige test van inline edit, assignment form, filters

---

## Fase 3: Route promotie — NDD wordt default (Complexiteit: Medium)

**Doel**: Hoofdroutes (`/`, `/opdrachten/`, etc.) serveren NDD templates. `/ndd/` prefix verdwijnt.

### 3a: Views omschakelen

- `PlacementListView.template_name` → `ndd/placements.html`, adopteer NDD template logica
- `AssignmentListView` → idem
- `UserListView` → idem
- Alle function-based views → NDD templates
- `client_modal` → altijd NDD template
- `inline_edit_view` → NDD inline edit templates
- Error handlers → NDD error templates

### 3b: URL patterns opschonen

- Verwijder alle `/ndd/` prefix routes
- Hoofdroutes serveren nu NDD content

### 3c: base.html vervangen

- `base.html` ← inhoud van `ndd/base.html` (zonder POC banner)
- Verwijder RVO CSS/JS includes, voeg NDD vendor assets toe

### 3d: Form layer omschakelen

- Alle forms: `RvoFormMixin` → `NlddFormMixin`
- `inline_edit/forms.py`: `_build_form()` gebruikt NDD mixin

### 3e: config/jinja2.py

- `setup_components(env)` kan voorlopig blijven (JRC tags worden niet meer gebruikt)

### Verificatie

- **Alle bestaande tests moeten slagen** (kritieke gate)
- Update `test_forms.py` assertions voor NDD patterns
- `grep -ri "rvo/" wies/core/` vangt achtergebleven referenties

---

## Fase 4: Opruimen (Complexiteit: Laag-Medium)

**Doel**: Verwijder alle RVO artefacten. Eenvoudig, schoon codebase.

### 4a: NDD templates verplaatsen naar root

- `ndd/placements.html` → `placements.html`
- `ndd/parts/*.html` → `parts/*.html`
- `ndd/forms/*.html` → vervangt `rvo/forms/*.html`
- Update alle `{% extends %}`, `{% include %}`, `render_to_string()` calls

### 4b: RVO artefacten verwijderen

- Delete `wies/core/jinja2/rvo/` directory
- Delete `wies/core/static/css/rvo_overwrite.css`
- Delete oude RVO-specifieke CSS (of update `base.css` om `var(--rvo-*)` te verwijderen)
- Delete oude JS bestanden die vervangen zijn door NDD equivalenten
- Delete `wies/core/static/roos/` vendor directory (RVO assets)

### 4c: Python infrastructuur vereenvoudigen

- `form_mixins.py` — Verwijder `RvoFormMixin`, hernoem `NlddFormMixin` naar `FormMixin`
- `views.py` — Verwijder `_is_ndd_request()`, `_ndd_redirect_url()`, NDD view subclasses
- `config/jinja2.py` — Verwijder `setup_components(env)`

### 4d: JRC dependency verwijderen

- `pyproject.toml` — Verwijder `jinja-roos-components`
- `config/jinja2.py` — Verwijder JRC import en registratie

### 4e: CSS consolidatie

- Merge `ndd/layout.css` met `base.css`
- Verwijder POC banner styles
- Verwijder `--rvo-*` CSS custom property usage

### 4f: Tests opschonen

- Verwijder `NDDIsolationTest`
- Verwijder `test_ndd_views.py`
- Update test assertions

### Verificatie

- `grep -ri "rvo" wies/core/` returns nul hits
- Volledige test suite groen

---

## Risico's en mitigatie

| Risico                           | Impact | Mitigatie                                                                               |
| -------------------------------- | ------ | --------------------------------------------------------------------------------------- |
| Form rendering regressie         | Hoog   | Fase 0 maakt NDD forms als aparte classes; bestaande forms worden pas in Fase 3 geraakt |
| Shadow DOM + HTMX                | Medium | NDD form templates gebruiken native HTML inputs (bewezen patroon uit POC filters)       |
| Inline editing templates         | Medium | Na Fase 3 is er maar 1 design system, template paden wijzen simpelweg naar NDD          |
| Assignment create (complex form) | Medium | Bouw voort op bestaand POC patroon; org picker JS kan gedeeld worden                    |
| Test assertions op CSS classes   | Laag   | Update test assertions in Fase 3                                                        |

---

## Fasesamenvatting

| Fase  | Scope                                       | Complexiteit | Gate                                          |
| ----- | ------------------------------------------- | ------------ | --------------------------------------------- |
| **0** | Form mixin + NDD form/inline-edit templates | Medium       | NDD forms renderen zonder RVO classes         |
| **1** | Alle ontbrekende NDD templates              | Medium-Hoog  | Elke pagina heeft NDD equivalent; tests groen |
| **2** | NDD JavaScript layer                        | Medium       | Alle JS werkt met NDD markup                  |
| **3** | Route promotie                              | Medium       | Hoofdroutes serveren NDD; tests groen         |
| **4** | Opruimen                                    | Laag-Medium  | Nul RVO referenties; dependency verwijderd    |
