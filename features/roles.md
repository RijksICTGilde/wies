# Roles and who may grant them

Wies separates authority by what it lets you do, not by seniority.

| Authority        | Where it lives           | In short                                          |
| ---------------- | ------------------------ | ------------------------------------------------- |
| Applicatiebeheer | `STAFF_EMAILS` (env var) | the maintenance pages, and nothing functional     |
| Office assistent | role (Django group)      | users, labels, merken and contract hours          |
| BDM              | role (Django group)      | any wies-sourced opdracht, and contract hours     |
| Consultant       | role (Django group)      | the text fields of an opdracht they are placed on |

What each may do is on the page **Beheer > Rollen**, which reads the rules
themselves.

Applicatiebeheer carries **no** functional rights. An application administrator
who also does assignment work holds `BDM` as well, and can test the app as a
normal user by unchecking it and checking it again; both steps are recorded as an
`Event`.

`Consultant` is also a population: `occupancy.py` filters Bezetting on
`user__groups__name=ROLE_CONSULTANT`, so a new colleague appears there only once
somebody gives them the role. That is why Office assistent may grant the roles;
onboarding would otherwise stall on an application administrator.

`STAFF_EMAILS` keeps the name it had when the authority was still called staff.

Code: `wies/core/roles.py`, rules in `wies/core/permissions.py`.

## A role's name is a key, its label is separate

`Group.name` is a key that never changes (`consultant`, `bdm`, `office_assistant`);
the screen name is `ROLE_LABELS` in `roles.py`. Matching uses
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
| Applicatiebeheer | nobody inside the application      |

`may_grant` answers the table and is the one place the policy lives: today it says
yes to every role, and no to Applicatiebeheer, which is not a role at all but an
address list. Restricting a role to Applicatiebeheer later is a line there and no
caller changed.

**What that costs, deliberately.** Office assistent may grant BDM, and BDM carries
every wies-sourced opdracht plus the ended and future placements of colleagues. So
user administration can hand out assignment authority. The alternative was to keep
BDM behind Applicatiebeheer, which would stall onboarding a Business Manager on a
deploy-level address list; the team chose onboarding.

Granting happens on the user sheet, Bewerken in the row menu on **Beheer >
Gebruikers**, open to Office assistent and Applicatiebeheer
(`may_administer_roles`). Nieuwe gebruiker is the same sheet under its own
`rijksauth.add_user`, and hands out roles under the same narrowing.
It is enforced twice: `UserForm(editor=...)` offers only the roles the editor may
grant, and that queryset is what a submitted id is validated against;
`_apply_groups` runs the same filter again and is the only `groups.set` in the
tree, so the sheet and the CSV import both pass it. It also keeps the roles the
editor may not grant, which today keeps nothing: the only thing `may_grant`
refuses is Applicatiebeheer, and that is an address list, not a `Group` anyone
holds. The half is the seam a future restriction would land in.

The sheet has two halves and the form offers each on its own gate, because the two
authorities do not overlap: the person (name, e-mail, merk, labels) on
`rijksauth.change_user`, the roles on `may_administer_roles`. Applicatiebeheer
holds the second without the first, so it gets a sheet with Rollen and nothing
else. A half the editor is not offered is not in `self.fields`, so it is absent
from `cleaned_data` and a submitted value for it is never written.

Under the form sits a third thing that is not part of it: the contract hours of
the linked colleague. `_contract_block` asks the rule and not the surface, in both
directions: it returns nothing to someone who may not read the hours, and carries
the buttons for whoever may keep them, on the user sheet and in the colleague
panel alike. That matters here because the sheet opens wider than the hours do:
Applicatiebeheer reaches it for the Rollen half and sees no hours.

*Which* periods it shows is the surface's question and not the rule's: the panel
lists the running and coming ones, the sheet the whole history. The two share the
three write routes, which cannot tell them apart, so every button carries the
surface it sits on (`?vanuit=paneel`) and the sheet posts back to the url it was
opened with. A save or a delete from the panel then swaps the panel's slice back
in. Guessing the surface from the route swaps the sheet's history into the panel,
ended periods and all.

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

## A rule, from declaration to answer

`permissions.py` holds the rules and nothing else: a list of `rule(...)` calls, no
functions and no names anything refers to, which is why the file looks like it
connects to nothing. It connects through a registry key, `(verb, model, field)`,
and that key is visible on neither side: in `permissions.py` you see the target,
at the call site you see the arguments.

`apps.py` imports the module in `ready()` purely for the side effect: the import
runs those calls and fills the registry. Everything else asks
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
registered without a row, and it refuses a relation outside `SCOPES`, which the
page would have no row to print.

There is one column per authority and never one per combination: roles add up, so
holding two means holding both columns. The rows underneath about visibility and
the screens are not rules; they ask their own predicate with a stand-in viewer.
Every such predicate has a row, `can_view_role_hours` (the hours on a colleague's
role, "Uren van de rol van een collega zien") included: a right nobody can look up
drifts unseen, and this one names the same audience as `rule(READ,
ContractPeriod)`, which the rows above print.

`test_role_matrix.py` fails when a printed cell differs from what the engine
answers a saved user, when a rule produces no row, or when a column stands for a
combination.

## Deploy

- `setup_roles()` (every container start) creates the three role groups;
  `Consultant` gets no Django permissions, all its rights are rules.
  Applicatiebeheer has no group at all, it is the address list.
- `rijksauth/0010` and `0011` move the groups from `Beheerder` to the key
  `office_assistant`, keeping members and permissions.
- `rijksauth/0012` drops the `Opdrachtbeheer` group and gives everyone in
  `STAFF_EMAILS` the `BDM` and `Office assistent` roles **once**, so an address
  added later does not get them and has to be granted on the user sheet. Whoever
  held the group itself gets `BDM`, address list or not: the roles screen handed
  `Opdrachtbeheer` out too, and dropping the group would otherwise take their
  rights along in silence.
- `ensure_initial_user` gives the first user of a fresh environment every group.

Without `STAFF_EMAILS` set, an environment has no application administrator at
all and nobody reaches the maintenance pages.

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

Two halves of that are already in place.

`all_of(OWN, BRANDS)` builds the relation that is both at once, so one grant reads
"a BDM, for an opdracht of their own merk, that they own":

```python
Grant(Role(ROLE_BDM), all_of(OWN, BRANDS))
```

How a combination is named, and why "either of these" needs no `any_of`, is in
`features/inline-editing.md`.

`Scope.parts` is what makes that readable to the matrix: a grant answers a row when
its parts are a subset of the row's, so `ANY` (no parts) covers every row and `OWN`
also covers the `OWN, BRANDS` row, without either being a special case.

`OWN` itself is named by no rule today, since a BDM carries every opdracht. It stays
as the narrowing this will combine with, and `ScopeVocabularyTest` measures it so it
cannot rot.

Two things are still missing:

- **An assignment has no merk.** It is derivable only via `owner.suborganization`,
  and both links are `SET_NULL`, so an assignment without an owner has no merk at
  all. Scoping needs a decision on that case, and on whether the merk follows the
  owner or is stored on the assignment.
- **A person has one merk, and a role has none.** `Colleague.suborganization` is a
  single FK and a `Group` is held or not, so "the merken this BDM holds the role
  for" has nowhere to live. The grant would need a model of its own, which then
  reaches the user sheet and `_apply_groups`.
