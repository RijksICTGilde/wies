"""The role matrix on ``/beheer/rollen/`` (``wies/core/role_matrix.py``).

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

from wies.core import role_matrix
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
    ROLE_BDM,
    ROLE_CONSULTANT,
    ROLE_OFFICE_ASSISTANT,
    is_staff_member,
    role_label,
    setup_roles,
)
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
_ICON = re.compile(r'<nldd-icon name="([^"]+)" color="([^"]+)"')


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
    headings = [heading for heading, _groups, _staff in role_matrix.COLUMNS]
    return {
        (label, heading): allowed
        for _title, rows in role_matrix.build_matrix()
        for label, cells in rows
        for heading, allowed in zip(headings, cells, strict=True)
    }


class RoleMatrixShapeTest(SimpleTestCase):
    def test_every_rule_becomes_a_row(self):
        """Completeness is structural (a rule *is* its rows); this is what that
        claim looks like from the outside."""
        in_the_table = {rule for _section, _label, rule, _scope in role_matrix.rule_rows()}

        assert in_the_table == set(registered_rules().values())

    def test_every_rule_lands_in_a_section_that_is_rendered(self):
        for rule in registered_rules().values():
            with self.subTest(rule=rule.label):
                assert role_matrix.section_of(rule.model) in role_matrix.SECTION_ORDER

    def test_every_extra_row_lands_in_a_section_that_is_rendered(self):
        for row in role_matrix.EXTRA_ROWS:
            with self.subTest(row=row.label):
                assert row.section in role_matrix.SECTION_ORDER

    def test_no_two_rows_carry_the_same_label(self):
        """Two relations can share a wording (both placed scopes do), so a rule
        that reached both would print the same row twice and the second would
        read as a contradiction of the first."""
        labels = [label for _section, label, _rule, _scope in role_matrix.rule_rows()]
        labels += [row.label for row in role_matrix.EXTRA_ROWS]

        assert len(labels) == len(set(labels)), sorted({label for label in labels if labels.count(label) > 1})

    def test_every_opdracht_rule_names_the_same_audience(self):
        """The rules on a dienst, a plaatsing and the opdracht's own fields each
        name the opdracht rule's audience instead of borrowing it, so this pins
        that they still agree."""
        opdracht = {Grant(Role(ROLE_BDM))}

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
        """A rule shows every relation it distinguishes; otherwise a BDM reads
        "Dienst bewerken (van een ander): Nee" and no row tells them about their own."""
        stand_ins = role_matrix.column_stand_ins()
        for rule in registered_rules().values():
            shown = role_matrix.row_scopes(rule)
            baseline = role_matrix.cells_for(rule, ANY, stand_ins)
            for scope in SCOPES_BY_MODEL[rule.model]:
                if role_matrix.cells_for(rule, scope, stand_ins) != baseline:
                    with self.subTest(rule=rule.label, scope=scope):
                        assert scope in shown

    def test_the_placed_rows_are_for_the_placed_consultant(self):
        """The rule branch behind them asks for the Consultant role on top of
        the placement, so no other role reaches them through the placement."""
        cells = _cells()
        # The placement grants it to the consultant; BDM is already through on the
        # relation-free grant these field rules name alongside it.
        allowed = {role_label(ROLE_CONSULTANT), "BDM"}

        for label in (
            "Naam van een opdracht bewerken",
            "Extra informatie bewerken",
            "Dienstomschrijving bewerken",
        ):
            for heading, _groups, _staff in role_matrix.COLUMNS:
                with self.subTest(row=label, column=heading):
                    assert cells[(f"{label} ({PLACED.label})", heading)] is (heading in allowed)
            assert not cells[(f"{label} ({ANY.label})", "Consultant")]

    def test_account_authority_reaches_the_colleague_record(self):
        """Whoever may edit someone else's account may edit their colleague record
        too. Only that direction is pinned, because only that direction holds; why the
        two models are separate at all is in ``features/roles.md``."""
        cells = _cells()

        for heading, _groups, _staff in role_matrix.COLUMNS:
            with self.subTest(column=heading):
                edits_account = cells[("Gebruiker bewerken (van een ander)", heading)]
                edits_colleague = cells[("Collega bewerken (van een ander)", heading)]
                assert not edits_account or edits_colleague

    def test_known_cells(self):
        """The scope splits the matrix exists for, pinned from the outside: the
        reader and the engine agree with each other by construction, so widening
        a rule moves both at once and only a named cell notices."""
        cells = _cells()

        assert cells[("Opdracht bewerken (van een ander)", "BDM")]
        assert not cells[("Opdracht bewerken (van een ander)", role_label(ROLE_OFFICE_ASSISTANT))]

        assert cells[("Gebruiker bewerken (je eigen)", "Consultant")]
        assert not cells[("Gebruiker bewerken (van een ander)", "Consultant")]
        assert cells[("Gebruiker bewerken (van een ander)", role_label(ROLE_OFFICE_ASSISTANT))]

        assert cells[("Collega bewerken (je eigen)", "Consultant")]
        assert not cells[("Collega bewerken (van een ander)", "Consultant")]
        assert cells[("Collega bewerken (van een ander)", role_label(ROLE_OFFICE_ASSISTANT))]

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
            # A heading is a label, which may hold a space ("Office assistent").
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
            "Afgelopen opdracht van een Business Manager zien": lambda u: (
                evaluate_assignment_visibility(*PAST, SimpleNamespace(user=u), TODAY).visible
            ),
            "Business management-sectie": lambda u: show_bm_page(SimpleNamespace(user=u)),
            "Gebruikerslijst openen": lambda u: self._page_opens(u, reverse("admin-users")),
            "Gebruiker aanmaken en verwijderen": lambda u: u.has_perms(["rijksauth.add_user", "rijksauth.delete_user"]),
            "E-mailadres wijzigen (van een ander)": lambda u: self._form_accepts(
                u, {"email": "nieuw-adres@rijksoverheid.nl"}
            ),
            "Rollen toekennen": lambda u: self._roles_screen_accepts(
                u, (ROLE_CONSULTANT, ROLE_BDM, ROLE_OFFICE_ASSISTANT)
            ),
            "Statistieken en database": is_staff_member,
        }
        # A new row needs a question here, or the stand-in could answer it wrongly unseen.
        assert set(questions) == {row.label for row in role_matrix.EXTRA_ROWS}

        cells = _cells()
        for label, ask in questions.items():
            for heading, user in self.users.items():
                with self.subTest(row=label, column=heading):
                    assert cells[(label, heading)] == ask(user)

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
                    assert any(cells[(row.label, heading)] for heading in headings)

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

    @override_settings(STAFF_EMAILS=[])
    def test_without_configured_addresses_staff_column_has_no_extra_rights(self):
        """Only what asks for no role at all is left: the SELF-scoped rules, plus
        seeing your own ended placement, which is a visibility rule and not a rule()."""
        cells = _cells()
        labels = {label for label, _heading in cells}

        assert {label for label in labels if cells[(label, role_matrix.STAFF)]} == {
            label for label in labels if label.endswith(f"({SELF.label})")
        } | {"Eigen afgelopen plaatsing zien"}


@override_settings(STAFF_EMAILS=[STAFF_EMAIL])
class RoleMatrixViewTest(TestCase):
    def setUp(self):
        setup_roles()
        self.url = reverse("role-matrix")

    def _user_admin(self):
        user = User.objects.create_user(email="gb@rijksoverheid.nl")
        user.groups.add(Group.objects.get(name=ROLE_OFFICE_ASSISTANT))
        return user

    def test_user_admin_sees_the_matrix_and_the_menu_entry(self):
        user = self._user_admin()
        self.client.force_login(user)

        response = self.client.get(self.url)

        assert response.status_code == 200
        content = response.content.decode()
        assert "Opdracht bewerken (van een ander)" in content
        assert "Can add user" in content
        assert content.count(f'<th scope="col">{role_matrix.STAFF}</th>') == len(role_matrix.SECTION_ORDER) + 1
        assert "Platformbeheer" not in content  # the term the page used to carry
        assert f' href="{self.url}"' in content  # sidebar
        assert f'data-href="{self.url}"' in content

    def test_every_cell_says_on_screen_what_the_matrix_answers(self):
        """The cells are the page, and nothing else asserts on the rendered ones:
        they are read from the table the reader builds, so a template that drops,
        shifts or inverts them is invisible to every other test here."""
        self.client.force_login(self._user_admin())

        rendered = _rendered_cells(self.client.get(self.url).content.decode())

        expected = {}
        for _title, rows in role_matrix.build_matrix():
            for label, cells in rows:
                # A row every column ticks is not this role's doing; the page marks those apart.
                tick = "Ja, ongeacht je rol" if all(cells) else "Ja"
                for index, allowed in enumerate(cells):
                    expected[(label, index)] = tick if allowed else "Nee"
        assert expected, "no rows to compare"
        for (label, index), word in expected.items():
            with self.subTest(row=label, column=role_matrix.COLUMNS[index][0]):
                assert rendered.get((label, index)) == word

    def test_the_legend_explains_every_icon_the_table_shows(self):
        """The grey tick means something the shape does not say ("not thanks to
        this role"), so an icon the legend skips leaves the reader guessing."""
        self.client.force_login(self._user_admin())

        html = self.client.get(self.url).content.decode()

        in_table = {
            _icon(cell) for row in _ROW.finditer(html) for cell in _CELL.findall(row.group("cells")) if _icon(cell)
        }
        in_legend = {_icon(term) for term in re.findall(r"<dt>(.*?)</dt>", html, re.S) if _icon(term)}
        assert in_table, "the table renders no icon at all"
        assert in_table == in_legend

    def test_the_cell_icons_are_names_the_design_system_knows(self):
        """An unknown icon name renders nothing, without an error: the cell would
        be empty on screen with only the hidden word behind it."""
        template = (Path(settings.BASE_DIR) / "wies/core/jinja2/role_matrix.html").read_text(encoding="utf-8")
        bundle = (Path(settings.BASE_DIR) / "wies/core/static/vendor/nldd/nldd.min.js").read_text(
            encoding="utf-8", errors="replace"
        )
        names = set(re.findall(r'<nldd-icon name="([^"]+)"', template))

        assert names, "the page renders no icon at all"
        for name in names:
            with self.subTest(icon=name):
                # The bundle spells a name either as a key or as a backticked alias.
                assert f'"{name}"' in bundle or f"`{name}`" in bundle

    def test_the_page_describes_a_placement_as_the_rows_print_it(self):
        """Two sentences on the page explain what being placed buys you: the
        paragraph above the tables and the legend entry for the grey tick. Neither
        may present a placement as role-free, because no placed row is.
        """
        placed = [
            label
            for _title, rows in role_matrix.build_matrix()
            for label, cells in rows
            if label.endswith(f"({PLACED.label})")
        ]
        assert placed, "no row about being placed at all"
        # The legend below puts this set in words, so a row about being placed on
        # an opdracht turning up here means that text has to be written again.
        grey = {label for _title, rows in role_matrix.build_matrix() for label, cells in rows if all(cells)}
        assert grey == {
            "Eigen afgelopen plaatsing zien",
            "Collega bewerken (je eigen)",
            "Gebruiker bewerken (je eigen)",
        }

        self.client.force_login(self._user_admin())
        html = self.client.get(self.url).content.decode()

        intro = next(p for p in re.findall(r"<p>(.*?)</p>", html, re.S) if "Waarop je geplaatst bent" in p)
        # The ways this paragraph has claimed the placed rows are role-free.
        for claim in ("gelijk", "ongeacht", "elke rol", "los van"):
            with self.subTest(claim=claim):
                assert claim not in intro
        legend = {
            _icon(term): " ".join(explanation.split())
            for term, explanation in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", html, re.S)
        }
        # Only one of the rows above is about a placement, and it is the reader's
        # own. Matched on the stem: "geplaatst" and "plaatsing" are one claim.
        explanation = legend[("check-circle-filled", "secondary-content")]
        for mention in re.finditer(r"\w*plaats\w*", explanation):
            with self.subTest(mention=mention.group()):
                assert explanation[: mention.start()].rstrip().endswith("je eigen"), explanation

    def test_the_page_names_no_exception_to_the_table(self):
        self.client.force_login(self._user_admin())

        content = " ".join(self.client.get(self.url).content.decode().split())

        assert "Naam van een opdracht bewerken (waarop je geplaatst bent)" in content
        for aside in ("niet in deze tabel", "staan niet in de tabel", "tegelijk"):
            with self.subTest(phrase=aside):
                assert aside not in content

    def test_who_may_grant_sees_the_link_to_the_users_page(self):
        """The third case reads the page and may grant nothing, so the link would
        lead to a closed door. Matched on the anchor the page text renders, not on
        the url: the sidebar carries that one under the same condition."""
        in_page_link = f'<a href="{reverse("admin-users")}">Gebruikers</a>'
        reader = User.objects.create_user(email="lezer@rijksoverheid.nl")
        reader.user_permissions.add(Permission.objects.get(codename="view_user"))
        for user, shown in (
            (self._user_admin(), True),
            (User.objects.create_user(email=STAFF_EMAIL), True),
            (User.objects.get(pk=reader.pk), False),
        ):
            with self.subTest(email=user.email):
                self.client.force_login(user)

                response = self.client.get(self.url)

                assert response.status_code == 200
                assert (in_page_link in response.content.decode()) is shown

    def test_staff_sees_the_matrix_and_its_menu_entry(self):
        self.client.force_login(User.objects.create_user(email=STAFF_EMAIL))

        assert self.client.get(self.url).status_code == 200
        assert self.url in self.client.get(reverse("staff-dashboard")).content.decode()

    def test_without_either_authority_is_closed(self):
        self.client.force_login(User.objects.create_user(email="consultant@rijksoverheid.nl"))

        response = self.client.get(self.url)

        assert response.status_code == 302
        assert response.url.startswith("/geen-toegang/")
