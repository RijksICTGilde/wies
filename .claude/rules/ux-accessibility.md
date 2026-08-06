# UX & Accessibility (WCAG/Dutch Government Standards)

## Language

- All UI text in Dutch
- Use formal "je" form
- Clear, concise labels

## Accessibility

- All form fields need labels (NLDD components handle this)
- Images need alt text
- Tables need headers and captions
- Color contrast must meet WCAG AA

## NLDD Design System

- Use @nldd/design-system web components for consistent look
- Follow nl-design-system patterns
- Reference: https://minbzk.github.io/storybook/

### Icons

Use the `<nldd-icon name="...">` web component from @nldd/design-system. Check the
storybook (https://minbzk.github.io/storybook/) or existing templates in
`wies/core/jinja2/` for valid icon names rather than guessing.

## Mobile

- Responsive layouts (NLDD components handle this)
- Touch-friendly button sizes
