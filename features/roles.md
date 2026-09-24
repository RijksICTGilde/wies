# Roles and who may grant them

Wies separates three kinds of authority, each named after what it lets you do.

| Authority        | Where it lives           | In short                                                  |
| ---------------- | ------------------------ | --------------------------------------------------------- |
| Applicatiebeheer | `STAFF_EMAILS` (env var) | the maintenance pages, granting every role                |
| Office assistent | role (Django group)      | users, labels and merken, granting all but Opdrachtbeheer |
| Opdrachtbeheer   | role (Django group)      | any wies-sourced assignment, whoever owns it              |

The job roles `Consultant` and `Business Development Manager` (BDM) sit next to
these. What each may do is on the page **Beheer > Rollen**, which reads the rules
themselves.

Applicatiebeheer carries **no** functional rights. An application administrator
who also does assignment work holds `Opdrachtbeheer` as well, and can test the app
as a normal user by unchecking it and checking it again; both steps are recorded
as an `Event`.

`Consultant` is also a population: `occupancy.py` filters Bezetting on
`user__groups__name=ROLE_CONSULTANT`, so a new colleague appears there only once
somebody gives them the role. That is why Office assistent may grant the job roles;
onboarding would otherwise stall on an application administrator.

`STAFF_EMAILS` keeps the name it had when the authority was still called staff.

Code: `wies/core/roles.py`, rules in `wies/core/permissions.py`.

## A role's name is a key, its label is separate

`Group.name` is a key that never changes (`consultant`, `bdm`, `office_assistant`,
`assignment_admin`); the screen name is `ROLE_LABELS` in `roles.py`. Matching uses
the key, showing uses `role_label(key)`, so renaming a role is one string and no
data migration.

Two places deliberately use the label instead:

- **The audit trail.** `Event.context['group_names']` stores the label as it was
  then. An event records how something was called when it happened.
- **The CSV import.** Column headers are labels, matched case-insensitively
  (`CSV_ROLE_COLUMNS`), so an import file stays readable.

## Who may grant what

| Role             | May be granted by                  |
| ---------------- | ---------------------------------- |
| Consultant       | Office assistent, Applicatiebeheer |
| BDM              | Office assistent, Applicatiebeheer |
| Office assistent | Office assistent, Applicatiebeheer |
| Opdrachtbeheer   | Applicatiebeheer                   |
| Applicatiebeheer | nobody inside the application      |

`may_grant` answers the table: everything is grantable by whoever reaches the roles
screen, except `ROLES_ONLY_STAFF_MAY_GRANT`, which is Applicatiebeheer's alone.
Applicatiebeheer itself is not a role: change `STAFF_EMAILS` and deploy.

Office assistent hands itself on because it is narrow: it touches no assignment,
sees no hidden placement, and `may_change_email` blocks taking over an application
administrator's address. Opdrachtbeheer stays apart because it reaches other
people's work and the ended placements of colleagues.

Granting happens on the user sheet, Bewerken in the row menu on **Beheer >
Gebruikers**, open to Office assistent and Applicatiebeheer
(`may_administer_roles`). Nieuwe gebruiker is the same sheet under its own
`rijksauth.add_user`, and hands out roles under the same narrowing.
It is enforced twice: `UserForm(editor=...)` offers only
the roles the editor may grant, and that queryset is what a submitted id is
validated against; `_apply_groups` drops the rest and keeps the roles the user
already holds, so setting someone's roles never strips their `Opdrachtbeheer`.

The sheet has two halves and the form offers each on its own gate, because the two
authorities do not overlap: the person (name, e-mail, merk, labels) on
`rijksauth.change_user`, the roles on `may_administer_roles`. Applicatiebeheer
holds the second without the first, so it gets a sheet with Rollen and nothing
else. A half the editor is not offered is not in `self.fields`, so it is absent
from `cleaned_data` and a submitted value for it is never written.

The users page itself opens for `may_view_users`, which is `rijksauth.view_user`
or `may_administer_roles`: Applicatiebeheer needs the list to pick a person. That
is all it gets. Nieuwe gebruiker and Verwijderen ask their own Django permission,
in the view and in the template that offers them.

Applicatiebeheer follows the email address, so moving an address to or from a
`STAFF_EMAILS` one is application administration too (`may_change_email`). The
inline-edit route for `email` is closed to everyone: it cannot see the new address,
so it cannot apply that check.

Creating asks the same question, with `""` as the address the account comes from:
a new user on a `STAFF_EMAILS` address is an application administrator the moment
their subject binds at login, so only Applicatiebeheer may put one there. Both
write paths ask it (`UserForm.clean_email` so the editor sees the reason,
`create_user` as the backstop), and the CSV import names the row it refuses,
because `create_user` would otherwise roll the whole file back from inside its
transaction without saying which line was the problem.

**Known tension:** BDM carries the visibility of colleagues' ended and future
placements, and Office assistent may grant BDM. Separating the two is its own
change.

## A rule, from declaration to answer

`permissions.py` holds the rules and nothing else: ten `rule(...)` calls, no
functions and no names anything refers to, which is why the file looks like it
connects to nothing. It connects through a registry key, `(verb, model, field)`,
and that key is visible on neither side: in `permissions.py` you see the target,
at the call site you see the arguments.

`apps.py` imports the module in `ready()` purely for the side effect: the import
runs the ten calls and fills the registry. Everything else asks
`has_permission(verb, obj, user, field=None)`, which looks that key up: the
inline-edit pencil and its POST, the delete and field routes, which fields a form
offers, and the panel's Verwijderen. The role page reads the same registry, which
is why it cannot drift from the code.

How a rule itself is written is in `features/inline-editing.md`, under
"Registering rules".

## Role page

`/beheer/rollen/` (for `rijksauth.view_user` or Applicatiebeheer) shows per role
what it may do on its own. `role_matrix.py` **reads** the rules rather than
repeating them: one row per relation, one column per authority. Completeness is
structural: `rule()` demands a `label` and a `grants`, so a right cannot be
registered without a row.

There is one column per authority and never one per combination: roles add up, so
holding two means holding both columns. The rows underneath about visibility and
the screens are not rules; they ask their own predicate with a stand-in viewer.

`test_role_matrix.py` fails when a printed cell differs from what the engine
answers a saved user, when a rule produces no row, or when a column stands for a
combination.

## Deploy

- `setup_roles()` (every container start) creates the four role groups;
  `Opdrachtbeheer` and `Consultant` get no Django permissions, all their rights
  are rules. Applicatiebeheer has no group at all, it is the address list.
- `rijksauth/0009_backfill_assignment_admin` gives everyone in `STAFF_EMAILS` the
  `Opdrachtbeheer` role **once**, so an address added later does not get it and has
  to be granted on the roles screen.
- `rijksauth/0010` and `0011` move the groups from `Beheerder` to the key
  `office_assistant`, keeping members and permissions.
- `ensure_initial_user` gives the first user of a fresh environment every group.

Without `STAFF_EMAILS` set, an environment has no application administrator at
all: nobody reaches the maintenance pages and nobody can grant `Opdrachtbeheer`.

## A person is a `User`, a `Colleague`, or both

`User` is the account Django requires, holding name, email and roles. `Colleague`
is the person as Wies shows them: placements, merk, labels, theme.
`Colleague.user` is a nullable one-to-one, so either half can stand alone: an
imported colleague has no account until that person logs in.

The user form writes name and email onto the `User` and merk and labels onto the
`Colleague` without asking anything of `Colleague`, so the rule there may not be
stricter than the one on `User`. Both therefore name `Role(ROLE_OFFICE_ASSISTANT)`
directly; neither goes through a Django model permission.

## Scoping by merk (#526)

The roles are global; limiting them to a merk is on the roadmap. A merk limit fits
as a `Scope`, like `OWN` and `PLACED`: the scope predicate already takes the grant
as a third argument, unused today, because this is the first one that needs it.
The question becomes "is this object's merk one you hold the role for".

Two things are missing first:

- **An assignment has no merk.** It is derivable only via `owner.suborganization`,
  and both links are `SET_NULL`, so an assignment without an owner has no merk at
  all. Scoping needs a decision on that case, and on whether the merk follows the
  owner or is stored on the assignment.
- **Group membership carries no merk.** A `Group` is held or not; there is nowhere
  to say "for merk X and Y". The grant would need a model of its own, which reaches
  the roles screen and `_apply_groups`.
