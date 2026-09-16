"""The role matrix on ``/beheer/rollen/`` (``wies/core/role_matrix.py``)."""

from datetime import date
from types import SimpleNamespace

from django.contrib.auth.models import Group
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from wies.core import role_matrix
from wies.core.editables import AssignmentEditables, ServiceEditables, UserEditables
from wies.core.models import Assignment, Colleague, Placement, Service
from wies.core.permission_engine import Verb, has_permission, registered_rules
from wies.core.roles import (
    ASSIGNMENT_ADMIN_GROUP_NAME,
    BDM_GROUP_NAME,
    CONSULTANT_GROUP_NAME,
    USER_ADMIN_GROUP_NAME,
    is_staff_member,
    setup_roles,
)
from wies.core.visibility_rules import evaluate_assignment_visibility, evaluate_placement_visibility, show_bm_page
from wies.rijksauth.models import User

STAFF_EMAIL = "platform@rijksoverheid.nl"
STAFF_EMAIL_2 = "platform-gb@rijksoverheid.nl"
COMBINED = "Platformbeheer met Gebruikersbeheer"


def _cells():
    headings = [heading for heading, _groups, _staff in role_matrix.COLUMNS]
    return {
        (label, heading): allowed
        for _title, rows in role_matrix.build_matrix()
        for label, cells in rows
        for heading, allowed in zip(headings, cells, strict=True)
    }


class RoleMatrixCoverageTest(TestCase):
    def test_every_registered_rule_has_a_row(self):
        covered = {row.rule for _title, rows in role_matrix.SECTIONS for row in rows if row.rule}

        assert set(registered_rules()) <= covered, set(registered_rules()) - covered


@override_settings(STAFF_EMAILS=[STAFF_EMAIL, STAFF_EMAIL_2])
class RoleMatrixStandInTest(TestCase):
    """The stand-in answers like a saved user with the same role."""

    def setUp(self):
        setup_roles()
        self.other = Colleague.objects.create(name="Ander", email="ander@rijksoverheid.nl", source="wies")
        self.other_user = User.objects.create_user(email="ander-account@rijksoverheid.nl")
        self.users = {}
        staff_emails = iter([STAFF_EMAIL, STAFF_EMAIL_2])
        for heading, groups, staff in role_matrix.COLUMNS:
            email = next(staff_emails) if staff else f"{heading.lower()}@rijksoverheid.nl"
            user = User.objects.create_user(email=email)
            Colleague.objects.create(name=heading, email=email, source="wies", user=user)
            user.groups.add(*Group.objects.filter(name__in=groups))
            self.users[heading] = User.objects.get(pk=user.pk)  # fresh, no cached permissions

    def _assignment(self, user, *, own):
        owner = user.colleague if own else self.other
        return Assignment.objects.create(name="Opdracht", source="wies", owner=owner)

    def _service(self, user, *, own):
        return Service.objects.create(assignment=self._assignment(user, own=own), description="d")

    def _group_ids(self, *names):
        return [str(pk) for pk in Group.objects.filter(name__in=names).values_list("pk", flat=True)]

    def _form_accepts(self, editor, changes):
        """Whether ``editor`` saves ``changes`` to another user through the user screen."""
        self.client.force_login(editor)
        data = {"first_name": "Ander", "last_name": "Account", "email": self.other_user.email, **changes}
        response = self.client.post(reverse("user-edit", args=[self.other_user.public_id]), data)
        # Restore, so the next question starts from the same user.
        User.objects.filter(pk=self.other_user.pk).update(email="ander-account@rijksoverheid.nl")
        self.other_user.groups.clear()
        return response.status_code == 302  # 403 without the gate, 200 with form errors

    def test_stand_in_matches_a_saved_user(self):
        past = (date(2000, 1, 1), date(2000, 1, 2))
        today = date(2000, 1, 3)
        questions = {
            "Opdracht bewerken (eigen)": lambda u: has_permission(Verb.UPDATE, self._assignment(u, own=True), u),
            "Opdracht bewerken (van een ander)": lambda u: has_permission(
                Verb.UPDATE, self._assignment(u, own=False), u
            ),
            "Opdracht verwijderen (eigen)": lambda u: has_permission(Verb.DELETE, self._assignment(u, own=True), u),
            "Opdracht verwijderen (van een ander)": lambda u: has_permission(
                Verb.DELETE, self._assignment(u, own=False), u
            ),
            "Naam van een opdracht bewerken (van een ander)": lambda u: has_permission(
                Verb.UPDATE, self._assignment(u, own=False), u, field=AssignmentEditables.name
            ),
            "Extra informatie bewerken (van een ander)": lambda u: has_permission(
                Verb.UPDATE, self._assignment(u, own=False), u, field=AssignmentEditables.extra_info
            ),
            "Dienst bewerken (van een ander)": lambda u: has_permission(Verb.UPDATE, self._service(u, own=False), u),
            "Dienstomschrijving bewerken (van een ander)": lambda u: has_permission(
                Verb.UPDATE, self._service(u, own=False), u, field=ServiceEditables.description
            ),
            "Teamlid verplaatsen (van een ander)": lambda u: has_permission(
                Verb.UPDATE, Placement.objects.create(colleague=self.other, service=self._service(u, own=False)), u
            ),
            "Eigen afgelopen plaatsing zien": lambda u: (
                evaluate_placement_visibility(*past, u.colleague.pk, SimpleNamespace(user=u), today).visible
            ),
            "Afgelopen plaatsing van een collega zien": lambda u: (
                evaluate_placement_visibility(*past, self.other.pk, SimpleNamespace(user=u), today).visible
            ),
            "Afgelopen opdracht van een Business Manager zien": lambda u: (
                evaluate_assignment_visibility(*past, SimpleNamespace(user=u), today).visible
            ),
            "Business management-sectie": lambda u: show_bm_page(SimpleNamespace(user=u)),
            "Gebruiker aanmaken en verwijderen": lambda u: u.has_perms(["rijksauth.add_user", "rijksauth.delete_user"]),
            "Gebruiker bewerken (van een ander)": lambda u: has_permission(Verb.UPDATE, self.other_user, u),
            "Eigen profiel bewerken": lambda u: has_permission(Verb.UPDATE, u, u),
            "E-mailadres wijzigen (van een ander)": lambda u: self._form_accepts(
                u, {"email": "nieuw-adres@rijksoverheid.nl"}
            ),
            "E-mailadres inline wijzigen (van een ander)": lambda u: has_permission(
                Verb.UPDATE, self.other_user, u, field=UserEditables.email
            ),
            "Collega bewerken (van een ander)": lambda u: has_permission(Verb.UPDATE, self.other, u),
            "Eigen collegagegevens bewerken": lambda u: has_permission(Verb.UPDATE, u.colleague, u),
            "Rol Consultant of BDM toekennen": lambda u: self._form_accepts(
                u, {"groups": self._group_ids(CONSULTANT_GROUP_NAME, BDM_GROUP_NAME)}
            ),
            "Rol Gebruikersbeheer of Opdrachtbeheer toekennen": lambda u: self._form_accepts(
                u, {"groups": self._group_ids(USER_ADMIN_GROUP_NAME, ASSIGNMENT_ADMIN_GROUP_NAME)}
            ),
            "Statistieken en database": is_staff_member,
        }
        cells = _cells()
        # A new row needs a question here, or the stand-in could answer it wrongly unseen.
        assert {label for label, _heading in cells} == set(questions)
        for label, ask in questions.items():
            for heading, user in self.users.items():
                with self.subTest(row=label, column=heading):
                    assert cells[(label, heading)] == ask(user)

    def test_known_cells(self):
        """The scope split the matrix exists for: BDM edits only its own assignment."""
        cells = _cells()

        assert cells[("Opdracht bewerken (eigen)", "BDM")]
        assert not cells[("Opdracht bewerken (van een ander)", "BDM")]
        assert cells[("Opdracht bewerken (van een ander)", "Opdrachtbeheer")]

    def test_user_screen_rows(self):
        cells = _cells()

        def column(label):
            return {heading for heading, _groups, _staff in role_matrix.COLUMNS if cells[(label, heading)]}

        assert column("Rol Consultant of BDM toekennen") == {"Gebruikersbeheer", COMBINED}
        assert column("Rol Gebruikersbeheer of Opdrachtbeheer toekennen") == {COMBINED}
        assert column("E-mailadres wijzigen (van een ander)") == {"Gebruikersbeheer", COMBINED}
        assert column("E-mailadres inline wijzigen (van een ander)") == {COMBINED}

    @override_settings(STAFF_EMAILS=[])
    def test_without_staff_emails_platform_column_has_no_extra_rights(self):
        """Consultant grants nothing, so it is the baseline of any logged-in user."""
        cells = _cells()
        labels = {label for label, _heading in cells}

        assert {label: cells[(label, "Platformbeheer")] for label in labels} == {
            label: cells[(label, "Consultant")] for label in labels
        }

    def test_building_the_matrix_only_reads(self):
        with CaptureQueriesContext(connection) as queries:
            role_matrix.build_matrix()
            role_matrix.group_permissions()

        assert queries.captured_queries
        assert all(q["sql"].lstrip().upper().startswith("SELECT") for q in queries.captured_queries)


@override_settings(STAFF_EMAILS=[STAFF_EMAIL])
class RoleMatrixViewTest(TestCase):
    def setUp(self):
        setup_roles()
        self.url = reverse("role-matrix")

    def test_user_admin_sees_the_matrix_and_the_menu_entry(self):
        user = User.objects.create_user(email="gb@rijksoverheid.nl")
        user.groups.add(Group.objects.get(name=USER_ADMIN_GROUP_NAME))
        self.client.force_login(user)

        response = self.client.get(self.url)

        assert response.status_code == 200
        content = response.content.decode()
        assert "Opdracht bewerken (van een ander)" in content
        assert "Can add user" in content
        assert f' href="{self.url}"' in content  # sidebar
        assert f'data-href="{self.url}"' in content

    def test_platform_admin_without_view_user_gets_no_menu_entry(self):
        self.client.force_login(User.objects.create_user(email=STAFF_EMAIL))

        response = self.client.get(reverse("staff-dashboard"))

        assert response.status_code == 200
        assert self.url not in response.content.decode()

    def test_without_view_user_is_forbidden(self):
        for email in ("consultant@rijksoverheid.nl", STAFF_EMAIL):
            with self.subTest(email=email):
                self.client.force_login(User.objects.create_user(email=email))

                assert self.client.get(self.url).status_code == 403
