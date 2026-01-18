# Wies Component Patterns

Patterns from the Wies codebase using jinja-roos-components.

## Headings

```jinja2
<c-h1>Pagina titel</c-h1>
<c-h1 noMargins>Titel zonder marge</c-h1>
<c-h2>Sectie titel</c-h2>
<c-h2 noMargins>Filters</c-h2>
```

## Buttons

```jinja2
<c-button kind="primary" type="submit">Opslaan</c-button>
<c-button kind="secondary" type="button">Annuleren</c-button>
<c-button kind="tertiary" hx-get="/url">Actie</c-button>
<c-button kind="warning">Verwijderen</c-button>
<c-button kind="warning-subtle">Annuleren</c-button>
```

With HTMX:
```jinja2
<c-button kind="primary"
          hx-post="{{ form_post_url }}"
          hx-target="#{{ target_element_id }}">
  Verzenden
</c-button>
```

## Alerts

```jinja2
<c-alert kind="info">Informatief bericht</c-alert>
<c-alert kind="success">Import geslaagd!</c-alert>
<c-alert kind="warning">Waarschuwingen:</c-alert>
<c-alert kind="error">Import mislukt</c-alert>
```

## Form Inputs

Text input:
```jinja2
<c-input name="field_name" placeholder="Zoeken..." />
<c-input type="text" name="name" required />
```

Select field:
```jinja2
<c-select-field
    name="filter_name"
    label="Filter label"
    hx-get="/filter-url"
    hx-target="#target">
  <option value="">Alle opties</option>
  {% for item in items %}
    <option value="{{ item.id }}">{{ item.name }}</option>
  {% endfor %}
</c-select-field>
```

File input:
```jinja2
<c-file-input-field accept=".csv" label="CSV-bestand" name="csv_file"/>
```

Date input:
```jinja2
<c-date-input-field
    name="start_date"
    label="Startdatum"
    hx-get="/filter-url"
    hx-target="#target" />
```

## Links

```jinja2
<c-link href="{{ url }}">Link tekst</c-link>
<c-link href="{{ static('file.csv') }}">Download bestand</c-link>
```

## Icons

```jinja2
<c-icon icon="zoek" color="logoblauw" size="md" />
<c-icon icon="kruis" color="grijs-700" size="sm" />
```

Common icons: `zoek`, `kruis`, `user`, `instellingen`
Sizes: `sm`, `md`, `lg`
Colors: `logoblauw`, `grijs-700`

## Modal Dialogs

Standard modal pattern (see `parts/generic_form_modal.html`):
```jinja2
<dialog id="{{ modal_element_id }}" class="modal-dialog" closedby="any">
  <div class="modal-content">
    <div class="modal-header">
      <h2 class="utrecht-heading-2">{{ modal_title }}</h2>
      <button type="button" class="close modal-close-button">&times;</button>
    </div>

    <form method="post" action="{{ form_post_url }}" hx-post="{{ form_post_url }}" hx-target="#{{ target_element_id }}">
      {{ get_csrf_hidden_input(request) }}
      <div class="modal-body">
        {{ content }}
      </div>
      <div class="modal-footer">
        <c-button kind="secondary" type="button">Annuleren</c-button>
        <c-button kind="primary" type="submit">{{ form_button_label }}</c-button>
      </div>
    </form>
  </div>
</dialog>
```

## Django Form Fields

Form fields render via `rvo/forms/field.html`:
```jinja2
<div class="utrecht-form-field">
  <div class="rvo-form-field__label">
    <label class="rvo-label rvo-label--required" for="{{ field.auto_id }}">
      {{ field.label }}
    </label>
  </div>
  {{ field }}
  {% if field.errors %}
    {{ field.errors }}
  {% endif %}
</div>
```

## RVO Layout Classes

Page layout:
```jinja2
<div class="rvo-layout-column rvo-layout-gap--3x">
  <div class="rvo-layout-column rvo-layout-gap--xl">
    {% block content %}{% endblock %}
  </div>
</div>
```

Max-width container:
```jinja2
<div class="rvo-max-width-layout rvo-max-width-layout-inline-padding--md">
  <!-- content -->
</div>
```

## RVO Links with Icons

For links with icons, use RVO classes (not jinja-roos-components):
```jinja2
<a href="{{ url }}" class="rvo-link rvo-link--with-icon rvo-link--no-underline rvo-link--logoblauw">
  <span class="utrecht-icon rvo-icon rvo-icon-user rvo-icon--md rvo-icon--logoblauw rvo-link__icon--before"
        role="img" aria-label="User"></span>
  {{ label }}
</a>
```
