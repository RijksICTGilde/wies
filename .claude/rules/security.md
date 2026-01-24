# Security Checklist

## Input Validation

- Validate all user input in forms
- Use Django's built-in validators
- Sanitize data before display (Jinja2 auto-escapes)

## Authentication

- Never bypass OIDC authentication
- Check permissions with `user_can_edit_*` functions
- Use `@login_required` decorator on views

## Data Access

- Filter querysets by user permissions
- Never expose raw SQL to users
- Use Django ORM for queries

## Sensitive Data

- No credentials in code
- Use environment variables for secrets
- Never log sensitive user data
