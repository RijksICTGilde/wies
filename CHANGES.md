# Changes

This files lists the changes during the lifetime of this project.

## unreleased

- 273: (squashed migrations) split out rijksauth app

## 2026-04-13

- 279: show historic placements and assignment (only to user themselves and assignment bm)
- 279: introduce editable userprofile
- 279: when colleague has multiple roles on 1 assignment, show on 1 line
- 287: bump zad-actions/deploy to v4
- 281: fix label delete bug introduced in 266
- 282: refactor UI polish, accessibility, and colleague model improvements
- 282: add location icons to assignment cards and colleague panel
- 282: fix XSS, input validation, and accessibility issues
- 282: show service description in team and colleague sidepanels
- 282: redesign placement table columns (Wie, Wat, Waar)
- 282: improve contrast: black links, headings, and icons (WCAG AA)
- 282: add RVO date, textarea, and checkbox widget templates
- 266: (migration) enforce uniqueness on Colleague.email + Colleague.source
- 266: always create Colleague for Users
- 266: (migration) move labels from User to Colleague
- 265: fix opdrachten filter to only consider skills on open services
- 265: make search bar on assignments page same as on wiezitwaar page
- 261: (new env var) move db admin from `/djadmin/db/` to `/staff/`, use SSO login instead of superuser login, access controlled by `STAFF_EMAILS`
- 262: make sidepanels the same between 2 pages
- 262: (migration) change status from assignment to service: (CONCEPT, OPEN, GESLOTEN)
- 251: fix that placement table shows org labels instead of org names
- 251: confirm search by enter press
- 251: add search suggestions: organizations found by abbreviation
- 253: use zad-actions v3
- 245: enable loading initial user via env var (also in production)
- 246: bump htmx to 2.0.8
- 246: bump Python to 3.14
- 246: bump Debian base image to trixie (Debian 13)
- 246: bump ruff to 0.15.6
- 246: bump GitHub Actions: login-action v4, build-push-action v7, setup-node v6
- 246: bump jinja-roos-components (RVO design-tokens 2.2.0, component-library 4.19.0, @nl-rvo/assets 1.0.0)
- 246: remove vendored RVO CSS and npm dependency — now served via jinja-roos-components
- 246: remove Node.js build stage from Dockerfile
- 246: migrate button classes from utrecht-button to rvo-button
- 246: rename color token logoblauw to lintblauw
- 253: persist filter and sort parameters in URL

## 2026-03-17_2

- 247: fix migration that there's only a single primary client
- 283: Implement HTMX for content swap in side panel
- 283: Align 'Toon meer' button with filterbar
- 283: Fix bug opdrachtgever not appearing on 'open opdrachten'
- 283: Show single org in filter when only 1 selected

## 2026-03-17 (invalid, use 2026-03-17_2)

- 221: include business manager assignments in colleague sidepanel
- 221: show period on assignment cards in colleague side panel
- 241: also delete organizationunits from admin db
- 164: introduce actions to automatically deploy on tag and PR
- 192: Add assignments page with organization hierarchy filter, multiselect role filter, and compact card layout
- 192: Support importing OPEN assignments via CSV
- 192: (migration) change VACATURE -> OPEN
- 220: support multiple organizations per assignment
- 220: (migration) add AssignmentOrganizationUnit.role (PRIMARY, INVOLVED)
- 220: make dummy data correct

## 2026-03-06

- add endpoint to worker container for health checks

## 2026-03-05

- 189: Add multi-select checkbox filters
- 189: Add multi-select dropdown in user create/edit modal
- 189: Add reusable multi_select component with search, clear, and keyboard support
- 185: improve docker-compose: remove container names, handle SIGTERM/SIGINT, change to port 8080
- 185: introduce js testing. `just test` runs both, `just test django` / `just test js` run individually
- 185: introduce small starting dataset and add `just load-full-data` for loading large dataset
- 185: (migration) introduce long running tasks through `db_worker` service
- 185: (migration) introduce hierarchial organization structure and synchronization
- bump django to 6.0.3

## 2026-03-03_3

- fix gunicorn, not using control socket

## 2026-03-03_2

- fix startup script not crashing on existing superuser
- fix django container properly waiting for db availability

## 2026-03-03

- 200: switch to PostgreSQL
- 200: run multiple workers in production
- 188: Scaling image on colleague card
- 201: fix pagination

## 2026-02-25

- 199: add db export and import functions for db migration
- 191 and others: bump ruff, gunicorn and cryptography (security)
- 176: Fix that externally managed assignment can not be edited
- 176: Filter out historical placements
- 172: Move dummy_data.json to wies/core/fixtures/
- 149: Change `/plaatsingen/importeren` to `/opdrachten/importeren`
- 149: Change home page from redirect to `/plaatsingen/` to serve placements directly at `/`
- 139: Skip login page, redirect directly to Keycloak (SSO-Rijk)
- 139: Improved "no access" page with context-specific messages based on email domain
- 139: Add `ALLOWED_EMAIL_DOMAINS` setting for ODI email validation
- 139: Add email domain validation to user create, edit and CSV import
- 147: Add security headers (CSP, Permissions-Policy, HSTS, etc.)
- 147: Serve vendor assets (htmx, RVO CSS) locally instead of from CDN
- 143: Bump Django from 5.2.9 to 6.0.1
- 144: Drop django-extensions
- 150: Add Wies logo to navbar item "Wie zit waar?"
- 162: Add pre-commit, ruff, djlint, pytest and coverage report
- 162: Add .editorconfig
- 162: Add GitHub action for labeling pre-commit PRs with label dependencies
- 162: Change formatting according to styling rules
- 161: Fix that BM link no longer resets active filters
- 163: Generalize assignment import to be brand independent
- 177: Refactor app layout: grid-based structure with collapsible sidebar, menubar, mobile responsive
- 177: Refactor base.html to use template includes (menubar, header_logo, filter_sidebar)
- 177: Mobile friendly screens: full-screen overlays for filters, side panel and modals
- 177: Refactor filter JS: extract shared functions to filter_utils.js
- 177: Clean up CSS/JS: CSS custom properties, overlay close registry, extract modals.css
- 177: Add animations to panels and sidebar
- 177: with env var SKIP_OIDC, skip login during development
- 181: Bump django security release

## 2026-01-19

- 136: fix bug with label filters returning wrong answers
- 136: (migration) Change ordering of filters: ministry, client, skill, labels alphabetically, period
- 136: Increase side panel width

## 2026-01-16

- 127: move placement filter in page, with chips
- 127: remove banner, remove jump in sidepanel, wider content
- 132: Update urls & dates from english to dutch
- 135: Styling menu items, adjust Layout, assignment not clickable, back button in side panel
- 133: Add 'Business Manager', change 'Beschrijving' (former 'Extra info') on assignment panel
- 133: (migration) Change assignment.extra_info to max 5000 chars
- 133: Add possibility to edit name and description of assignment by business manager and consultants working on assignment
- 133: Fix ministry and client link from side panel triggering filter

## 2026-01-14

- (backwards incompatible) clean slate - start over with only essential 4W functionality
- Change login to only pass when user is in database
- Remove login requirement from logout endpoint
- Remove possibility to switch off authentication
- Developer is added as user from env vars during setup
- Generalized modal css from filter bar
- Introduce roles (groups) Beheerder, Consultant, Business Development Manager
- Users page with filtering, search, create, edit and delete (only admins)
- Add tests for authentication and user views
- Introduce forms.py/RVOMixin to enable style the form with roos
- Add /users/import csv upload for sourcing starting userlist
- Upgrade to jrc 0.3
- Remove actions menu on assignment
- Introduce "wies" as extra source on records
- Developer user during setup now gets all roles
- Add /placements/import csv upload for sourcing RIG placement list
- Upgrade to django 5.2.9 for security patch
- (migration) Remove hours_per_week on service and placement
- (migration) Make email unique in db
- Fix that RVOMixin uses proper jinja environment (enabling components and other functions)
- 114: Implement right-side panel with colleague and assignment details
- 114: Add support for combining panel & filter URLs
- 114: Remove legacy detail pages
- 114: Add filtering for clients and ministries from panel
- 113: replace brand table with label system for more flexibility
- 113: dedicated admin page for user and label management
- 113: move django admin panel to `/djadmin/`
- 113: fix enter press in user search does not trigger user create
- 113: generalized user_form_modal -> generic_form_modal
- add wies email adress to no-access page
- 102: Add Event model with events 'User.create', 'User.update', 'User.delete', 'Login.success', 'Login.fail'
- 123: Side menu instellingen pagina fully to left
- 123: Styling navigation
- 123: Delete functionality to modal
- 123: Update behaviour gebruikers and labels table rows
- 123: Update showModal behaviour for closing
- 123: Change layout user modal
- 123: Aligned modals
- bump authlib due to path vulnerability

## 2025-10-09

- add period filter to placement page
- add end date of current placement to colleague list
- add availability sorting to colleague list
- (backwards incompatible) change assignment status. new list: LEAD, VACATURE, INGEVULD, AFGEWEZEN
- changed that assignment phase is computed instead of assigned
- changed to also unavailble colleagues are shown when checking out matches
- fix source data to have correct Placement.period_source
- bump authlib dependency due to security patch
- saved note redirects to notes tab, whitespace underneath note form, always show note form
- changed availability timeline: dont show placements outside range
- changed availability timeline: brand and ODI skill filter added to modal, removed client and ministery
- added to availability timeline: start month input
- added search to main navigation
- added search results page
- bump django to 5.2.7 due to CVE (unaffected)
- update clients page
- update page names
- clean up css
- improve query performance
- introduce pagination on placements and colleagues
- remove dashboard page
- move brand filter inside modal
- upgrade rvo token and components to latest
- change tag styling
- introduce "VACATURE" entries in dummy data

## 2025-09-19

- update dependencies to latest, including django security release
- fix that a cancel action on create/edit/remove takes user back to page from which action was perfomed
- add breadcrumbs on client detail page
- add underline active state to main tabs

## 2025-08-21

- add user profile page with RVO tab navigation (Overzicht, Opdrachten, CV, Instellingen)
- link user accounts to colleague profiles via email matching
- add auto-create colleague on login
- add profile edit functionality through existing colleague update form
- add Colleague.email, remove duplicates in dummy data
- add search on assignment "Extra info"
- add possibility to take over hours per week from service
- fix Placement update form dynamic field visibility
- fix RVO mixin to have email and numberfield
- add notes: create and list from assignment detail page
- add possibility for primary action on filter group
- add create assignment button and move organisation into filter modal
- split assignment page into two tabs: services and notes
- nest placement creation under service
- update looks of services/placements
- add link to relevant colleague page for matching

## 2025-08-18

- add dashboard page as landing page with summary cards
- add summary cards to dashboard, clients and assignment detail pages
- add clickable table rows with hover states to all dashboard tables
- add service layer for statistics calculations across all pages
- change environment variables into .env file
- add openidconnect authentication
- update colleague page with RVO design system components and improved layout
- consolidate CSS files - move placement styles to custom.css
- fix Python import statements placed incorrectly within functions
- standardize RVO/Utrecht design system class usage across templates
- fix assignment page filter context and navigation layout
- add service.otys api module
- add syncing between OTYS IIR and wies colleagues

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
