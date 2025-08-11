# Changes
This files lists the changes during the lifetime of this project.

## demo-2025-08-18
- combine dashboard tabs "Eindigt binnen 1 maand" and "Eindigt binnen 3 maanden" into "Opdrachten die binnenkort aflopen"
- make dashboard the landing page instead of placements table
- add clickable table rows with hover states to all dashboard tables
- remove chevron columns from dashboard tables for cleaner look
- extract dashboard statistics to service layer (StatisticsService)
- refactor assignment statistics to use service layer
- convert dashboard tabs from JavaScript to HTMX for better performance
- move CSS and JavaScript from templates to separate files
- improve code organization and maintainability

## Current version

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
