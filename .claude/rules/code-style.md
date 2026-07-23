# Code Style

## Python

- Python 3.14+ with type hints on public functions
- Use `uv` for package management
- Format with `ruff format`, lint with `ruff check --fix`
- When adding `# noqa` comments, always include what the rule enforces and why the suppression is justified here (e.g. `# noqa: F401 (unused import), PLC0415 (import not at top level) — Django signal registration must happen inside ready()`)

## Comments

Follow the [Google style guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) principle (applies to all languages here, not just Python): comment the non-obvious, not the code that already reads for itself.

- Explain _why_, or what is surprising — not _what_ a line plainly does.
- Skip comments that restate the code (`// commit on blur` above a blur listener adds nothing).
- Keep the ones that save a reader from a wrong assumption: re-entrancy, ordering constraints, workarounds, why a guard exists, why a non-obvious approach was chosen.
- Prefer one tight comment over a multi-line block. A block that keeps growing is usually a hint the code wants a clearer name or a small refactor.

## Django

- Models in `wies/core/models.py`
- Use `verbose_name` for Dutch field labels
- ForeignKey: use `related_name` and `on_delete=models.CASCADE`
- Querysets in `querysets.py` for complex queries
- Use `django.utils.timezone.now()` for current time (not `datetime.now()` or `datetime.utcnow()`)

## Templates (Jinja2)

- Located in `wies/core/jinja2/`
- Use RVO macros from jinja-roos-components
- Dutch labels for all user-facing text

## JavaScript

De Content-Security-Policy is `script-src 'self'` — geen `'unsafe-inline'`, geen nonce.
Inline JavaScript wordt door de browser stil geblokkeerd (dode knop, alleen een
console-warning), dus:

- Geen `<script>`-blokken in templates; altijd een bestand in `wies/core/static/js/`.
- Geen `onclick=`/`onsubmit=`/`hx-on` en **geen `@click=` op c-componenten** —
  jinja-roos-components compileert die naar `onclick=`.
- Bind gedrag met een data-attribuut en handel het af in `static/js/ui_handlers.js`:
  `data-action="<naam>"` (klik, met een entry in `CLICK_ACTIONS`), `data-confirm="<vraag>"`
  (bevestiging voor gewone formulieren; op htmx-formulieren `hx-confirm` gebruiken),
  `data-keyboard-activate` (Enter activeert een niet-focusbaar klikbaar element).
- Gebruik geen styling-class als gedrag-hook; een CSS-rename sloopt dan stil de binding.

`wies/core/tests/test_templates_no_inline_js.py` bewaakt dit en faalt de build.

## Commits

- English commit messages
- Reference issue numbers where applicable
