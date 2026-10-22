"""The role matrix on ``/beheer/rollen/`` (``wies/core/services/role_matrix.py``).

What these tests check is the reader: that the cell the page prints for a rule
and a relation is the answer the engine gives a saved user acting on a saved row.
"""

import re
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from wies.core.models import Assignment, Colleague, ContractPeriod, Placement, Service
from wies.core.permission_engine import (
    ANY,
    OWN,
    PLACED,
    PLACED_ON_SERVICE,
    SELF,
    Grant,
    Role,
    registered_rules,
)
from wies.core.roles import (
    ROLE_BUSINESS_MANAGER,
    ROLE_CONSULTANT,
    ROLE_USER_ADMIN,
    can_view_role_hours,
    is_staff_member,
    role_label,
    setup_roles,
)
from wies.core.services import role_matrix
from wies.core.visibility_rules import evaluate_assignment_visibility, evaluate_placement_visibility, show_bm_page
from wies.rijksauth.models import User

STAFF_EMAIL = "applicatiebeheer@rijksoverheid.nl"

# Every relation a model can stand in, so a rule is asked about relations it does
# not mention as well as the ones it does.
SCOPES_BY_MODEL = {
    Assignment: (OWN, PLACED, ANY),
    Service: (OWN, PLACED, PLACED_ON_SERVICE, ANY),
    Placement: (OWN, PLACED, ANY),
    Colleague: (SELF, ANY),
    ContractPeriod: (ANY,),
    User: (SELF, ANY),
}

PAST = (date(2000, 1, 1), date(2000, 1, 2))
TODAY = date(2000, 1, 3)


_ROW = re.compile(r'<tr>\s*<th scope="row">(?P<label>[^<]*)</th>(?P<cells>.*?)</tr>', re.S)
_CELL = re.compile(r"<td>(.*?)</td>", re.S)
_HIDDEN_WORD = re.compile(r'wies-visually-hidden">([^<]*)<')
_ICON = re.compile(r'<nldd-icon icon="([^"]+)" color="([^"]+)"')


def _icon(markup):
    """``(name, color)`` of the icon in a cell or a legend term, if it has one."""
    match = _ICON.search(markup)
    return match.groups() if match else None


def _rendered_cells(html):
    """``{(row label, column index): what the cell says}``.

    The word only counts when an icon is rendered beside it; a cell missing
    either comes back as its raw markup, so the failure names it.
    """
    cells = {}
    for row in _ROW.finditer(html):
        for index, cell in enumerate(_CELL.findall(row.group("cells"))):
            word = _HIDDEN_WORD.search(cell)
            cells[(row.group("label"), index)] = word.group(1) if word and "<nldd-icon" in cell else cell.strip()
    return cells


def _cells():
    """``{(row header, column heading): allowed}``, keyed by the header the page prints."""
    headings = [heading for heading, _groups, _staff in role_matrix.COLUMNS]
    return {
        (header, heading): allowed
        for _title, rows in role_matrix.build_matrix()
        for header, cells in rows
        for heading, allowed in zip(headings, cells, strict=True)
    }


def _headers():
    return [header for _title, rows in role_matrix.build_matrix() for header, _cells in rows]


def _role_free(header):
    return f"{role_matrix.ROLE_FREE_NOTE})" in header


def _row(label, relation=""):
    """The printed header of one row, found by its label and the relation it names.

    Without a relation, a label that only prints with the role-free note counts too.
    """
    prefix = f"{label} ({relation}" if relation else f"{label} ({role_matrix.ROLE_FREE_NOTE})"
    matches = [h for h in _headers() if (h == label and not relation) or h.startswith(prefix)]
    assert len(matches) == 1, (label, relation, matches)
    return matches[0]


class RoleMatrixShapeTest(SimpleTestCase):
    def test_every_rule_becomes_a_row(self):
        """Completeness is structural (a rule *is* its rows); this is what that
        claim looks like from the outside."""
        in_the_table = {rule for _section, _label, _relation, rule, _scope in role_matrix.rule_rows()}

        assert in_the_table == set(registered_rules().values())

    def test_every_relation_a_rule_names_gets_a_row_of_its_own(self):
        """``rule_rows`` lays the rows out by walking ``SCOPES``, so a relation
        outside that tuple is named by ``row_scopes`` and printed by nothing. The
        rule would still be enforced, and the page would be quiet about it;
        ``rule()`` refuses such a scope, and this is that refusal seen from the
        page's end."""
        printed = {(rule, scope) for _section, _label, _relation, rule, scope in role_matrix.rule_rows()}

        for rule in registered_rules().values():
            for scope in role_matrix.row_scopes(rule):
                with self.subTest(rule=rule.label, scope=scope):
                    assert (rule, scope) in printed

    def test_every_rule_lands_in_a_section_that_is_rendered(self):
        for rule in registered_rules().values():
            with self.subTest(rule=rule.label):
                assert role_matrix.section_of(rule.model) in role_matrix.SECTION_ORDER

    def test_every_extra_row_lands_in_a_section_that_is_rendered(self):
        for row in role_matrix.EXTRA_ROWS:
            with self.subTest(row=row.label):
                assert row.section in role_matrix.SECTION_ORDER

    def test_no_two_rows_carry_the_same_label(self):
        """Two relations sharing a wording, or a relation left unnamed on a rule
        with more than one row, would print the same row twice and the second
        would read as a contradiction of the first."""
        labels = [(label, relation) for _section, label, relation, _rule, _scope in role_matrix.rule_rows()]
        labels += [(row.label, "") for row in role_matrix.EXTRA_ROWS]

        assert len(labels) == len(set(labels)), sorted({label for label in labels if labels.count(label) > 1})

    def test_every_opdracht_rule_names_the_same_audience(self):
        """The rules on a dienst, a plaatsing and the opdracht's own fields each
        name the opdracht rule's audience instead of borrowing it, so this pins
        that they still agree."""
        opdracht = {Grant(Role(ROLE_BUSINESS_MANAGER))}

        for key, rule in registered_rules().items():
            verb, model, field = key
            if model not in (Assignment, Service, Placement):
                continue
            with self.subTest(rule=f"{verb}:{model.__name__}" + (f".{field}" if field else "")):
                assert opdracht <= set(rule.grants)

    def test_no_column_stands_for_a_combination_of_authorities(self):
        """Roles add up, so every column is one authority; a combination column
        would read as if the combination were an authority of its own."""
        for heading, groups, staff in role_matrix.COLUMNS:
            with self.subTest(column=heading):
                assert len(groups) + int(staff) == 1


@override_settings(STAFF_EMAILS=[STAFF_EMAIL])
class RoleMatrixReaderTest(TestCase):
    """The table against the engine, with saved users and saved rows."""

    def setUp(self):
        setup_roles()
        self.other = Colleague.objects.create(name="Ander", email="ander@rijksoverheid.nl", source="wies")
        self.other_user = User.objects.create_user(email="ander-account@rijksoverheid.nl")
        self.fixtures = {heading: self._build(heading, groups, staff) for heading, groups, staff in role_matrix.COLUMNS}

    def _build(self, heading, groups, staff):
        email = STAFF_EMAIL if staff else f"{heading.lower().replace(' ', '-')}@rijksoverheid.nl"
        user = User.objects.create_user(email=email)
        colleague = Colleague.objects.create(name=heading, email=email, source="wies", user=user)
        user.groups.add(*Group.objects.filter(name__in=groups))
        user = User.objects.get(pk=user.pk)  # fresh, so no permission cache from before the groups

        own, own_service = self._assignment("Eigen", colleague)
        # Placed on one dienst of this opdracht, so its sibling is "placed on the
        # opdracht but not on this dienst": the difference between the two placed
        # scopes.
        placed, placed_service = self._assignment("Geplaatst", self.other)
        sibling_service = Service.objects.create(assignment=placed, description="Zusterdienst", source="wies")
        other, other_service = self._assignment("Van een ander", self.other)
        return SimpleNamespace(
            user=user,
            colleague=colleague,
            objects={
                (Assignment, OWN): own,
                (Assignment, PLACED): placed,
                (Assignment, ANY): other,
                (Service, OWN): own_service,
                (Service, PLACED): sibling_service,
                (Service, PLACED_ON_SERVICE): placed_service,
                (Service, ANY): other_service,
                (Placement, OWN): self._place(own_service, self.other),
                (Placement, PLACED): self._place(placed_service, colleague),
                (Placement, ANY): self._place(other_service, self.other),
                (ContractPeriod, ANY): self._contract(self.other),
                (Colleague, SELF): colleague,
                (Colleague, ANY): self.other,
                (User, SELF): user,
                (User, ANY): self.other_user,
            },
        )

    def _assignment(self, name, owner):
        assignment = Assignment.objects.create(name=name, source="wies", owner=owner)
        return assignment, Service.objects.create(assignment=assignment, description="Dienst", source="wies")

    def _place(self, service, colleague):
        return Placement.objects.create(colleague=colleague, service=service, source="wies")

    def _contract(self, colleague):
        return ContractPeriod.objects.create(colleague=colleague, hours_per_week=36, start_date=date(2000, 1, 1))

    def test_every_rule_row_matches_a_saved_user(self):
        stand_ins = role_matrix.column_stand_ins()
        for rule in registered_rules().values():
            for scope in SCOPES_BY_MODEL[rule.model]:
                printed = role_matrix.cells_for(rule, scope, stand_ins)
                for index, (heading, _groups, _staff) in enumerate(role_matrix.COLUMNS):
                    fixtures = self.fixtures[heading]
                    with self.subTest(rule=rule.label, scope=scope, column=heading):
                        assert printed[index] == bool(rule(fixtures.user, fixtures.objects[(rule.model, scope)]))

    def test_a_relation_that_changes_the_answer_gets_a_row(self):
        """A rule shows every relation it distinguishes; otherwise a Business Manager reads
        "Dienst bewerken (van een ander): Nee" and no row tells them about their own."""
        stand_ins = role_matrix.column_stand_ins()
        for rule in registered_rules().values():
            shown = role_matrix.row_scopes(rule)
            baseline = role_matrix.cells_for(rule, ANY, stand_ins)
            for scope in SCOPES_BY_MODEL[rule.model]:
                if role_matrix.cells_for(rule, scope, stand_ins) != baseline:
                    with self.subTest(rule=rule.label, scope=scope):
                        assert scope in shown

    def test_the_placed_rows_hold_for_every_role(self):
        """Being placed is enough: a team member without the Consultant role (an OR
        member, another ODI colleague) keeps these fields too. Somebody else's
        opdracht still asks for the Business Manager role."""
        cells = _cells()

        # The relation per row, because a dienst names the narrower one: your own
        # placement, not anywhere on the opdracht.
        for label, scope in (
            ("Naam van een opdracht wijzigen", PLACED),
            ("Opdrachtomschrijving wijzigen", PLACED),
            ("Taken wijzigen", PLACED_ON_SERVICE),
        ):
            for heading, _groups, _staff in role_matrix.COLUMNS:
                with self.subTest(row=label, column=heading):
                    assert cells[(_row(label, scope.label), heading)]
            assert not cells[(_row(label, ANY.label), "Consultant")]

    def test_account_authority_reaches_the_colleague_record(self):
        """Whoever may edit someone else's account may edit their colleague record
        too. Only that direction is pinned, because only that direction holds; why the
        two models are separate at all is in ``docs/roles.md``."""
        cells = _cells()

        for heading, _groups, _staff in role_matrix.COLUMNS:
            with self.subTest(column=heading):
                edits_account = cells[(_row("Gebruiker wijzigen", ANY.label), heading)]
                edits_colleague = cells[(_row("Collega wijzigen", ANY.label), heading)]
                assert not edits_account or edits_colleague

    def test_known_cells(self):
        """The scope splits the matrix exists for, pinned from the outside: the
        reader and the engine agree with each other by construction, so widening
        a rule moves both at once and only a named cell notices."""
        cells = _cells()

        # A rule with one row names no relation: there is nothing to tell apart.
        assert cells[("Opdracht wijzigen", role_label(ROLE_BUSINESS_MANAGER))]
        assert not cells[("Opdracht wijzigen", role_label(ROLE_USER_ADMIN))]

        assert cells[("Gebruiker wijzigen (je eigen, ongeacht je rol)", "Consultant")]
        assert not cells[("Gebruiker wijzigen (van een ander)", "Consultant")]
        assert cells[("Gebruiker wijzigen (van een ander)", role_label(ROLE_USER_ADMIN))]

        assert cells[("Collega wijzigen (je eigen, ongeacht je rol)", "Consultant")]
        assert not cells[("Collega wijzigen (van een ander)", "Consultant")]
        assert cells[("Collega wijzigen (van een ander)", role_label(ROLE_USER_ADMIN))]

    def test_the_table_only_reads(self):
        """Nothing about the matrix may write, and nothing may probe: the queries
        left are the ones for the Django permissions in the table underneath."""
        with CaptureQueriesContext(connection) as queries:
            role_matrix.build_matrix()
            role_matrix.group_permissions()

        assert queries.captured_queries
        assert all(q["sql"].lstrip().upper().startswith("SELECT") for q in queries.captured_queries)
        assert not [q for q in queries.captured_queries if "core_placement" in q["sql"]]


@override_settings(STAFF_EMAILS=[STAFF_EMAIL])
class RoleMatrixExtraRowTest(TestCase):
    """The rows that are not rules, against saved users with the same roles."""

    def setUp(self):
        setup_roles()
        self.other = Colleague.objects.create(name="Ander", email="ander@rijksoverheid.nl", source="wies")
        self.other_user = User.objects.create_user(email="ander-account@rijksoverheid.nl")
        self.users = {}
        for heading, groups, staff in role_matrix.COLUMNS:
            # A heading is a label, which may hold a space ("Business Manager").
            email = STAFF_EMAIL if staff else f"{heading.lower().replace(' ', '-')}@rijksoverheid.nl"
            user = User.objects.create_user(email=email)
            Colleague.objects.create(name=heading, email=email, source="wies", user=user)
            user.groups.add(*Group.objects.filter(name__in=groups))
            self.users[heading] = User.objects.get(pk=user.pk)  # fresh, no cached permissions

    def _group_ids(self, *names):
        return sorted(str(pk) for pk in Group.objects.filter(name__in=names).values_list("pk", flat=True))

    def _form_accepts(self, editor, changes):
        """Whether ``editor`` saves ``changes`` to another user through the user screen."""
        self.client.force_login(editor)
        data = {"first_name": "Ander", "last_name": "Account", "email": self.other_user.email, **changes}
        response = self.client.post(reverse("user-edit", args=[self.other_user.public_id]), data)
        saved = User.objects.get(pk=self.other_user.pk)
        stored = {"email": saved.email}
        # Restore, so the next question starts from the same user.
        User.objects.filter(pk=self.other_user.pk).update(email="ander-account@rijksoverheid.nl")
        # No on 403 (gate), 200 (form errors) or a 302 that dropped the change.
        return response.status_code == 302 and all(stored[key] == value for key, value in changes.items())

    def _page_opens(self, visitor, url):
        """Whether ``visitor`` actually gets the page, not whether a predicate says so."""
        self.client.force_login(visitor)
        return self.client.get(url).status_code == 200

    def _roles_screen_accepts(self, editor, group_names):
        """Whether ``editor`` saves these roles on another user through the user sheet.

        The person half rides along unchanged; an editor who is not offered it does
        not have it read back."""
        self.client.force_login(editor)
        asked = self._group_ids(*group_names)
        data = {"first_name": "Ander", "last_name": "Account", "email": self.other_user.email, "groups": asked}
        response = self.client.post(reverse("user-edit", args=[self.other_user.public_id]), data)
        stored = sorted(str(pk) for pk in self.other_user.groups.values_list("pk", flat=True))
        # Restore, so the next question starts from the same user.
        self.other_user.groups.clear()
        return response.status_code == 302 and stored == asked

    def test_every_extra_row_matches_a_saved_user(self):
        questions = {
            "Eigen afgelopen plaatsing zien": lambda u: (
                evaluate_placement_visibility(*PAST, u.colleague.pk, SimpleNamespace(user=u), TODAY).visible
            ),
            "Afgelopen plaatsing van een collega zien": lambda u: (
                evaluate_placement_visibility(*PAST, self.other.pk, SimpleNamespace(user=u), TODAY).visible
            ),
            "Afgelopen opdracht op het profiel van een Business Manager zien": lambda u: (
                evaluate_assignment_visibility(*PAST, SimpleNamespace(user=u), TODAY).visible
            ),
            "Business management openen": lambda u: show_bm_page(SimpleNamespace(user=u)),
            # The predicate reads only ``colleague_id``, so the placement need not be
            # saved; the user is, which is what this test compares against.
            "Uren per week van een geplaatste collega zien": lambda u: can_view_role_hours(
                u, Placement(colleague_id=self.other.pk)
            ),
            "Gebruikers, labels, merken en rollen openen": lambda u: all(
                self._page_opens(u, reverse(name))
                for name in ("admin-users", "label-admin", "suborganization-admin", "role-matrix")
            ),
            "Gebruiker toevoegen en verwijderen": lambda u: u.has_perms(
                ["rijksauth.add_user", "rijksauth.delete_user"]
            ),
            "E-mailadres wijzigen in het gebruikersformulier": lambda u: self._form_accepts(
                u, {"email": "nieuw-adres@rijksoverheid.nl"}
            ),
            "Rollen toekennen": lambda u: self._roles_screen_accepts(
                u, (ROLE_CONSULTANT, ROLE_BUSINESS_MANAGER, ROLE_USER_ADMIN)
            ),
            "Statistieken en database zien": lambda u: (
                is_staff_member(u) and self._page_opens(u, reverse("staff-dashboard"))
            ),
        }
        # A new row needs a question here, or the stand-in could answer it wrongly unseen.
        assert set(questions) == {row.label for row in role_matrix.EXTRA_ROWS}

        cells = _cells()
        for label, ask in questions.items():
            for heading, user in self.users.items():
                with self.subTest(row=label, column=heading):
                    assert cells[(_row(label), heading)] == ask(user)

    def test_no_extra_row_needs_a_combination_of_columns(self):
        """A row that only a combination may do is "Nee" in every column, which
        reads as "niemand kan dit" while somebody can. (A row nobody may do at
        all is fine: it is true.)"""
        everything = role_matrix.stand_in(
            [group for _heading, groups, _staff in role_matrix.COLUMNS for group in groups], staff=True
        )
        cells = _cells()
        headings = [heading for heading, _groups, _staff in role_matrix.COLUMNS]

        for row in role_matrix.EXTRA_ROWS:
            if row.check(everything):
                with self.subTest(row=row.label):
                    assert any(cells[(_row(row.label), heading)] for heading in headings)

    def test_group_permissions_match_a_saved_user(self):
        headings = [heading for heading, _groups, _staff in role_matrix.COLUMNS]
        table = role_matrix.group_permissions()

        for index, heading in enumerate(headings):
            with self.subTest(column=heading):
                held = set(Permission.objects.filter(group__user=self.users[heading]).values_list("name", flat=True))
                assert {name for name, cells in table if cells[index]} == held
        assert {name for name, _cells in table} == set(
            Permission.objects.filter(group__user__in=self.users.values()).values_list("name", flat=True)
        )

    def test_the_matrix_does_not_depend_on_the_environment(self):
        """The page shows what each role may do, so the address list of this
        environment changes nothing: the Applicatiebeheerder column is the role's
        answer with the list empty, set, or naming somebody else."""
        expected = role_matrix.build_matrix()
        for addresses in ([], ["iemand-anders@rijksoverheid.nl"]):
            with self.subTest(staff_emails=addresses), override_settings(STAFF_EMAILS=addresses):
                assert role_matrix.build_matrix() == expected

    @override_settings(STAFF_EMAILS=[])
    def test_the_staff_column_holds_the_maintenance_pages_without_configured_addresses(self):
        cells = _cells()
        assert cells[("Statistieken en database zien", role_matrix.STAFF)]

    def test_the_stand_in_counts_as_staff_only_while_the_matrix_is_built(self):
        """Its address is not a way in: outside ``build_matrix`` it is nobody."""
        stand_in = role_matrix.stand_in((), staff=True)
        assert not is_staff_member(stand_in)


@override_settings(STAFF_EMAILS=[STAFF_EMAIL])
class RoleMatrixViewTest(TestCase):
    def setUp(self):
        setup_roles()
        self.url = reverse("role-matrix")

    def _user_admin(self):
        user = User.objects.create_user(email="gb@rijksoverheid.nl")
        user.groups.add(Group.objects.get(name=ROLE_USER_ADMIN))
        return user

    def test_user_admin_sees_the_matrix_and_the_menu_entry(self):
        user = self._user_admin()
        self.client.force_login(user)

        response = self.client.get(self.url)

        assert response.status_code == 200
        content = response.content.decode()
        assert "Opdracht wijzigen" in content
        assert "Can add user" in content
        assert content.count(f'<th scope="col">{role_matrix.STAFF}</th>') == len(role_matrix.SECTION_ORDER) + 1
        assert "Platformbeheer" not in content  # the term the page used to carry
        assert f' href="{self.url}"' in content  # sidebar
        assert f'data-href="{self.url}"' in content

    def test_every_cell_says_on_screen_what_the_matrix_answers(self):
        """The cells are the page, and nothing else asserts on the rendered ones:
        they are read from the table the reader builds, so a template that drops,
        shifts or inverts them is invisible to every other test here.

        Two words and no third: a cell says ja or nee. Whether the whole row is
        role-free is said in the row header, which is why the key here is the
        header the page prints.
        """
        self.client.force_login(self._user_admin())

        rendered = _rendered_cells(self.client.get(self.url).content.decode())

        expected = {}
        for _title, rows in role_matrix.build_matrix():
            for header, cells in rows:
                for index, allowed in enumerate(cells):
                    expected[(header, index)] = "Ja" if allowed else "Nee"
        assert expected, "no rows to compare"
        assert set(expected.values()) == {"Ja", "Nee"}, "a cell state nobody renders"
        for (header, index), word in expected.items():
            with self.subTest(row=header, column=role_matrix.COLUMNS[index][0]):
                assert rendered.get((header, index)) == word

    def test_the_legend_explains_every_icon_the_table_shows(self):
        """An icon the legend skips leaves the reader guessing, and one the legend
        keeps after the table stopped printing it sends them looking for it."""
        self.client.force_login(self._user_admin())

        html = self.client.get(self.url).content.decode()

        in_table = {
            _icon(cell) for row in _ROW.finditer(html) for cell in _CELL.findall(row.group("cells")) if _icon(cell)
        }
        in_legend = {_icon(term) for term in re.findall(r"<dt>(.*?)</dt>", html, re.S) if _icon(term)}
        assert in_table, "the table renders no icon at all"
        assert in_table == in_legend

    def test_every_legend_term_says_its_state_in_words(self):
        """The legend is the explanation for whoever does not see the colour, so a
        term that is only an icon is blank for exactly that reader: ``nldd-icon``
        sets its own ``aria-hidden``. Same rule as the cells, asserted apart,
        because the icon comparison above passes with or without the word."""
        self.client.force_login(self._user_admin())

        html = self.client.get(self.url).content.decode()

        terms = re.findall(r"<dt>(.*?)</dt>", html, re.S)
        assert terms, "the legend has no terms"
        for term in terms:
            word = _HIDDEN_WORD.search(term)
            with self.subTest(icon=_icon(term)):
                assert word is not None, term.strip()
                assert word.group(1) in {"Ja", "Nee"}, term.strip()

    def test_the_cell_icons_are_names_the_design_system_knows(self):
        """An unknown icon name renders nothing, without an error: the cell would
        be empty on screen with only the hidden word behind it."""
        template = (Path(settings.BASE_DIR) / "wies/core/jinja2/role_matrix.html").read_text(encoding="utf-8")
        bundle = (Path(settings.BASE_DIR) / "wies/core/static/vendor/nldd/nldd.min.js").read_text(
            encoding="utf-8", errors="replace"
        )
        names = set(re.findall(r'<nldd-icon icon="([^"]+)"', template))

        assert names, "the page renders no icon at all"
        for name in names:
            with self.subTest(icon=name):
                # The bundle spells a name either as a key or as a backticked alias.
                assert f'"{name}"' in bundle or f"`{name}`" in bundle

    def test_only_a_row_every_column_ticks_is_called_role_free(self):
        """The note replaces the grey tick, so it carries the claim the colour used
        to: this row asks for no role at all.

        Both directions, because the note is read from the cells and a row that
        gained a "Nee" must lose it. The set is spelled out as well: these rows
        are what the page's explanation of the note is written about, so a new
        one arriving here means that sentence has to be written again.
        """
        cells = _cells()
        headings = [heading for heading, _groups, _staff in role_matrix.COLUMNS]

        for header in _headers():
            with self.subTest(row=header):
                assert _role_free(header) == all(cells[(header, heading)] for heading in headings)

        assert {header for header in _headers() if _role_free(header)} == {
            "Eigen afgelopen plaatsing zien (ongeacht je rol)",
            "Collega wijzigen (je eigen, ongeacht je rol)",
            "Gebruiker wijzigen (je eigen, ongeacht je rol)",
            "Naam van een opdracht wijzigen (waarop je geplaatst bent, ongeacht je rol)",
            "Opdrachtomschrijving wijzigen (waarop je geplaatst bent, ongeacht je rol)",
            "Taken wijzigen (je eigen plaatsing, ongeacht je rol)",
        }

    def test_every_row_about_being_placed_is_called_role_free(self):
        """Being placed is enough, so every placed row reads as role-free, and the
        paragraph that explains the placed wordings asks for no role on top."""
        # Both relations: they word themselves differently, and a filter on one of
        # them would quietly stop checking the rows of the other.
        wordings = tuple(f"({scope.label}" for scope in (PLACED, PLACED_ON_SERVICE))
        placed = [header for header in _headers() if any(w in header for w in wordings)]
        assert placed, "no row about being placed at all"
        for header in placed:
            with self.subTest(row=header):
                assert _role_free(header)

        self.client.force_login(self._user_admin())
        html = self.client.get(self.url).content.decode()

        intro = next(p for p in re.findall(r"<p>(.*?)</p>", html, re.S) if "Waarop je geplaatst bent" in p)
        # The ways this paragraph has claimed a placement needs a role on top.
        for claim in ("daarbovenop", "nog een rol", "rol uit de kolom"):
            with self.subTest(claim=claim):
                assert claim not in intro

    def test_the_page_explains_the_note_it_prints(self):
        """The note is words, not a colour, and words the reader has not met need
        saying once. The role-free rows are about yourself and the opdrachten you
        are placed on, so the explanation has to name both.
        """
        self.client.force_login(self._user_admin())
        html = self.client.get(self.url).content.decode()
        note = role_matrix.ROLE_FREE_NOTE.strip()

        headers = [row.group("label") for row in _ROW.finditer(html)]
        assert [header for header in headers if note in header], "the page prints no note at all"

        explanation = next(
            " ".join(p.split()) for p in re.findall(r"<p>(.*?)</p>", html, re.S) if note in p and "<th" not in p
        )
        assert "jezelf" in explanation, explanation
        assert "geplaatst" in explanation, explanation

    def test_the_page_names_no_exception_to_the_table(self):
        self.client.force_login(self._user_admin())

        content = " ".join(self.client.get(self.url).content.decode().split())

        assert "Naam van een opdracht wijzigen (waarop je geplaatst bent, ongeacht je rol)" in content
        for aside in ("niet in deze tabel", "staan niet in de tabel", "tegelijk"):
            with self.subTest(phrase=aside):
                assert aside not in content

    def test_the_user_admin_sees_the_link_to_the_users_page(self):
        """Matched on the anchor the page text renders and not on the url: the
        sidebar carries that one under its own condition."""
        in_page_link = f'<a href="{reverse("admin-users")}">Gebruikers</a>'
        self.client.force_login(self._user_admin())

        response = self.client.get(self.url)

        assert response.status_code == 200
        assert in_page_link in response.content.decode()

    def test_neither_staff_nor_a_loose_view_user_opens_the_matrix(self):
        """The page belongs to the Gebruikersbeheerder; the Applicatiebeheerder keeps
        the maintenance pages and is not offered it there either."""
        reader = User.objects.create_user(email="lezer@rijksoverheid.nl")
        reader.user_permissions.add(Permission.objects.get(codename="view_user"))
        staff = User.objects.create_user(email=STAFF_EMAIL)
        for user in (staff, User.objects.get(pk=reader.pk)):
            with self.subTest(email=user.email):
                self.client.force_login(user)

                assert self.client.get(self.url).status_code == 302

        self.client.force_login(staff)
        assert self.url not in self.client.get(reverse("staff-dashboard")).content.decode()

    def test_without_either_authority_is_closed(self):
        self.client.force_login(User.objects.create_user(email="consultant@rijksoverheid.nl"))

        response = self.client.get(self.url)

        assert response.status_code == 302
        assert response.url.startswith("/geen-toegang/")
