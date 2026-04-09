# UX & Accessibility (WCAG/Dutch Government Standards)

## Language

- All UI text in Dutch
- Use formal "je" form
- Clear, concise labels

## Accessibility

- All form fields need labels (RVO components handle this)
- Images need alt text
- Tables need headers and captions
- Color contrast must meet WCAG AA

## RVO Design System

- Use RVO components for consistent look
- Follow nl-design-system patterns
- Reference: https://github.com/nl-design-system/rvo

### RVO Icons

Never guess `rvo-icon-*` class names — they are Dutch and unpredictable. Always look them up first:

```bash
python3 -c "
import json; from pathlib import Path
f = Path('.venv/lib/python3.14/site-packages/jinja_roos_components/overall_definitions.json')
icons = json.loads(f.read_text()).get('icons', [])
for i in icons:
    name = i['name'] if isinstance(i, dict) else i
    if 'SEARCH_TERM' in name.lower(): print(name)
"
```

Replace `SEARCH_TERM` with a Dutch keyword (e.g. `slot` for lock, `zoek` for search, `verwijder` for delete).

## Mobile

- Responsive layouts (RVO handles this)
- Touch-friendly button sizes
