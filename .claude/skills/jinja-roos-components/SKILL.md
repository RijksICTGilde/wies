---
name: jinja-roos-components
description: Create UI components using jinja-roos-components library. Use when building forms, buttons, modals, or any frontend elements in Wies templates.
---

# Jinja ROOS Components

## Overview

Wies uses jinja-roos-components from RijksICTGilde for UI components.
Repository: https://github.com/RijksICTGilde/jinja-roos-components

## Component Syntax

Components use custom HTML-like tags with `c-` prefix:

```jinja2
<c-component-name attribute="value">Content</c-component-name>
```

## Available Components

### Headings

- `<c-h1>` / `<c-h2>` - Headings with optional `noMargins` attribute

### Buttons

- `<c-button kind="primary|secondary|tertiary|warning|warning-subtle">`

### Alerts

- `<c-alert kind="info|success|warning|error">`

### Form Inputs

- `<c-input>` - Text input
- `<c-select-field>` - Dropdown select
- `<c-file-input-field>` - File upload
- `<c-date-input-field>` - Date picker

### Other

- `<c-link>` - Links
- `<c-icon icon="" color="" size="">` - Icons

## Styling & Layout

For layout, use RVO CSS classes:

- `rvo-layout-column`, `rvo-layout-gap--xl` - Layout
- `rvo-max-width-layout` - Container

## Forms

Django forms use RVOMixin for styling. Form fields render via `rvo/forms/field.html`.

## Fallback Reference

For CSS classes not covered by jinja-roos-components:

- RVO Design System: https://github.com/nl-design-system/rvo

Read `components.md` for detailed usage patterns from the Wies codebase.
