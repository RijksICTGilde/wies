# Roles and who may grant them

Wies separates three kinds of authority. Each is named after what it lets you
do, not after who holds it.

| Authority | Where it lives | In short |
|---|---|---|
| Platformbeheer | `STAFF_EMAILS` (env var) | the platform pages, granting the privileged roles |
| Gebruikersbeheer | role (Django group) | users, labels and merken |
| Opdrachtbeheer | role (Django group) | any wies-sourced assignment, whoever owns it |

The job roles `Consultant` and `Business Development Manager` (BDM) sit next
to these. What each role may do is on the page **Beheer > Rollen** (see below).

Platformbeheer carries **no** functional rights. A platform administrator who
also does assignment work holds `Opdrachtbeheer` as well. To test the app as a
normal user, uncheck your own `Opdrachtbeheer` in the user screen and check it
again afterwards; both steps are recorded as an `Event`.

Code: `wies/core/roles.py` (`is_staff_member`, `is_assignment_admin`,
`is_bdm_or_assignment_admin`), rules in `wies/core/permissions.py`.

## Who may grant what

Only Platformbeheer creates privilege: the privileged roles
(`STAFF_GRANTED_GROUPS` in `roles.py`) may be granted by Platformbeheer only,
the job roles by Gebruikersbeheer as well (`may_grant`). Platformbeheer itself
is granted by nobody inside the application: change `STAFF_EMAILS` and deploy.
Granting happens in the user screen, so it also takes Gebruikersbeheer.

The rule is enforced in two places:

- `UserForm(editor=...)` leaves them out of the role choices for anyone who is
  not a platform administrator. They are not shown, and a submitted id for one
  of them fails form validation.
- `_apply_groups` in `services/users.py` (used by `create_user` and
  `update_user`, so also by the CSV import) drops them from the submitted roles
  and keeps the ones the user already holds. A Gebruikersbeheer user editing
  someone with Opdrachtbeheer therefore does not strip it. The `User` event
  records the roles the user ends up with in `group_names`.

Platformbeheer follows the email address, so changing an email to or from a
`STAFF_EMAILS` address is platform administration too (`may_change_email` in
`roles.py`). `UserForm` rejects it for anyone else and `update_user` refuses
it. The generic inline-edit route for `email` is platform administration only
(`update_user_email` in `permissions.py` says why).

The CSV import has a `Gebruikersbeheer` column (formerly `Beheerder`); it only
takes effect when a platform administrator runs the import. For anyone else
the import lists each row whose role was dropped as a warning.

## Role page

`/beheer/rollen/` (Beheer > Rollen, for `rijksauth.view_user`) shows per role
what it may do on its own, and the Django permissions per group. The cells are
not written by hand: `wies/core/role_matrix.py` asks the real rules
(`has_permission`, the visibility rules, `may_grant`) for a stand-in user with
one role, acting on unsaved objects, so the page only reads. A row about the
user screen asks the screen's gate (`change_user`) as well as the rule the form
applies. Platformbeheer with Gebruikersbeheer is the one combination that may do
more than its parts, so it has its own column. A placed consultant's extra
rights need a placement in the database and are named in the page text instead.

`test_role_matrix.py` fails when a registered `@rule` has no row, or when the
stand-in answers differently from a saved user with the same role.

## Deploy

- `setup_roles()` (every container start) creates both groups; `Opdrachtbeheer`
  has no Django model permissions, all its rights are rules.
- Migration `rijksauth/0009_backfill_assignment_admin` gives everyone in the
  environment's `STAFF_EMAILS` the `Opdrachtbeheer` role, once, so nobody loses
  a right they had.
- Migration `rijksauth/0010_rename_beheerder_group` renames `Beheerder` to
  `Gebruikersbeheer`, keeping members and permissions.
- `ensure_initial_user` still gives the first user of a fresh environment
  every group.

## Known tension

The BDM role carries the visibility of colleagues' ended and future
placements, and Gebruikersbeheer may grant BDM. Separating that visibility from
BDM is a separate change.

## Scoping by merk (#526)

The roles are global today; limiting them to a merk is on the roadmap. Keep
these seams intact so that change stays local:

- **Predicates are asked with the object in hand.** Edit and delete rights on
  an assignment reach `is_assignment_admin` and `is_bdm` only from the rules in
  `permissions.py`, which receive the assignment. Scoping then changes the rule
  bodies, not their call sites. The row-visibility checks
  (`evaluate_*_visibility`, `_services_visible_changes`) have the row too, but
  ask `is_bdm_or_assignment_admin(request)`, a per-request cached answer; scoping
  them means passing the assignment in and caching per merk. The Business
  management gate (`business_management_access_required`, `show_bm_page`) has
  no object and stays "holds the role"; the rows on those pages then need a
  merk filter.
- **Group names live in `roles.py`.** Querysets import the constants
  (`_bdm_queryset` uses `BDM_GROUP_NAME`) instead of spelling names. The
  exception today is `CONSULTANT_GROUP` in `services/occupancy.py`.

Open data question: an assignment has no merk of its own. It can only be
derived via `owner.suborganization`, and both links are nullable
(`Assignment.owner` and `Colleague.suborganization` are `SET_NULL`). Scoping
needs a decision on who may act on an assignment without an owner or merk,
and on whether the assignment's merk follows its owner (moves when the owner
changes merk or is replaced) or is stored on the assignment.
