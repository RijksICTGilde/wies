# Changes
This files lists the changes during the lifetime of this project.

## unreleased
- add period filter to placement page
- add end date of current placement to colleague list
- add availability sorting to colleague list
- (backwards incompatible) change assignment status. new list: LEAD, VACATURE, INGEVULD, AFGEWEZEN
- changed that assignment phase is computed instead of assigned
- changed to also unavailble colleagues are shown when checking out matches
- fix source data to have correct Placement.period_source
- bump authlib dependency due to security patch

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
