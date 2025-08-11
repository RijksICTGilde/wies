# Changes
This files lists the changes during the lifetime of this project.

## Current version
### Dashboard Summary Cards & Service Layer Refactoring
**Resultaat:** Verbeterde gebruikerservaring en code architectuur voor dashboard en statistieken

**Gebruikerservaring verbeteringen:**
- Dashboard is nu de landingspagina voor betere toegankelijkheid
- Samengevoegde tabs voor opdrachten die binnenkort aflopen (binnen 3 maanden)
- Klikbare tabel rijen met hover states voor betere interactie
- Cleaner interface door verwijdering van overbodige chevron kolommen

**Technische verbeteringen:**
- Service layer geïntroduceerd voor alle statistieken berekeningen
- Code duplicatie opgelost tussen dashboard en clients pagina's
- HTMX implementatie voor moderne, snelle tab switching
- Betere scheiding van concerns (CSS/JS uit templates)
- Verbeterde code organisatie en maintainability

**Impact:**
- Consistentie tussen alle pagina's die statistieken tonen
- Herbruikbare statistieken functionaliteit
- Moderne web development best practices
- Betere performance door server-side rendering
- Professionelere codebase architectuur

## demo-2025-08-11

## demo-2025-08-11
- add gunicorn for production server
- add whitenoise for static file serving
- change that you only need container start for production
- add db admin page `/admin/db/`
- change settings into `local` and `production`
- change `production` settings
- change dummy data: remove illogical combination, add more
- add WRITABLE_FOLDER env var for db
- fix static files not found
- remove rvo assets from static files and add as dependency
- add syncing between exact and wies colleagues

## demo-2025-08-04
...
