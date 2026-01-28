# Changes

This files lists the changes during the lifetime of this project.

## unreleased

- 147: Add security headers (CSP, Permissions-Policy, HSTS, etc.)
- 147: Serve vendor assets (htmx, RVO CSS) locally instead of from CDN
- 143: Bump Django from 5.2.9 to 6.0.1
- 144: Drop django-extensions
- 162: Add pre-cmmit, ruff, djlint, pytest and coverage report
- 162: Add .editor.config
- 162: Add Github action for labeling pre-commit PRs with label dependencies
- 162: Change formatting according to styling rules
- 161: Fix that BM link no longer resets active filters
- 177: Collapse filters
- 177: Screens, modals and panels responsive
- 177: Add logo to login
- 177: Refactor layout to be more flexible

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
