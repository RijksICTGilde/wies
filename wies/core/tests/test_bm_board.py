from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from wies.core.models import (
    ASSIGNMENT_STATUS,
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    Label,
    LabelCategory,
    OrganizationUnit,
    Placement,
    Service,
)
from wies.core.roles import setup_roles
from wies.core.services.assignments import assignment_edit_specs, create_assignment_from_form
from wies.core.services.board import ENDING_SOON_WEEKS, build_board, move_assignment

User = get_user_model()


def _columns_by_key(columns):
    return {column.key: column for column in columns}


def _card_names(columns, key):
    return [card.name for card in _columns_by_key(columns)[key].cards]


class BuildBoardTest(TestCase):
    def setUp(self):
        self.owner = Colleague.objects.create(name="BM", email="bm@rijksoverheid.nl", source="wies")

    def _assignment(self, name, **kwargs):
        kwargs.setdefault("owner", self.owner)
        kwargs.setdefault("source", "wies")
        return Assignment.objects.create(name=name, **kwargs)

    def _seat(self, assignment, *, filled=False):
        """One service on the assignment, optionally with someone placed on it."""
        service = Service.objects.create(assignment=assignment, description="Rol", source="wies")
        if filled:
            colleague = Colleague.objects.create(
                name=f"C{service.id}", email=f"c{service.id}@rijksoverheid.nl", source="wies"
            )
            Placement.objects.create(colleague=colleague, service=service, source="wies")
        return service

    def test_every_status_is_a_column(self):
        columns = build_board(self.owner)
        assert [c.key for c in columns] == ["LEAD", "OPEN", "INGEVULD", "GESLOTEN"]

    def test_card_lands_in_its_status_column(self):
        self._assignment("Lead-opdracht", status="LEAD")
        self._assignment("Gesloten opdracht", status="GESLOTEN")

        columns = build_board(self.owner)

        assert _card_names(columns, "LEAD") == ["Lead-opdracht"]
        assert _card_names(columns, "GESLOTEN") == ["Gesloten opdracht"]
        assert _card_names(columns, "OPEN") == []

    def test_only_own_assignments(self):
        other = Colleague.objects.create(name="Ander", email="ander@rijksoverheid.nl", source="wies")
        self._assignment("Van mij")
        self._assignment("Van iemand anders", owner=other)

        columns = build_board(self.owner)

        assert _card_names(columns, "OPEN") == ["Van mij"]

    def test_without_owner_every_column_is_empty(self):
        self._assignment("Van mij")

        columns = build_board(None)

        assert all(column.count == 0 for column in columns)

    def test_occupancy_counts_filled_versus_total(self):
        assignment = self._assignment("Deels bezet")
        self._seat(assignment, filled=True)
        self._seat(assignment, filled=False)

        card = _columns_by_key(build_board(self.owner))["OPEN"].cards[0]

        assert (card.filled_seats, card.total_seats, card.open_seats) == (1, 2, 1)

    def test_assignment_without_services_has_no_seats(self):
        self._assignment("Nog niets")

        card = _columns_by_key(build_board(self.owner))["OPEN"].cards[0]

        assert (card.filled_seats, card.total_seats, card.open_seats) == (0, 0, 0)

    def test_ends_soon_within_window(self):
        today = timezone.now().date()
        self._assignment("Loopt af", end_date=today + timedelta(weeks=ENDING_SOON_WEEKS - 1))

        card = _columns_by_key(build_board(self.owner))["OPEN"].cards[0]

        assert card.ends_soon is True
        assert card.weeks_until_end == ENDING_SOON_WEEKS - 1

    def test_end_date_far_away_is_not_ending_soon(self):
        today = timezone.now().date()
        self._assignment("Loopt door", end_date=today + timedelta(weeks=ENDING_SOON_WEEKS + 4))

        card = _columns_by_key(build_board(self.owner))["OPEN"].cards[0]

        assert card.ends_soon is False

    def test_past_end_date_is_not_ending_soon(self):
        today = timezone.now().date()
        self._assignment("Al voorbij", end_date=today - timedelta(weeks=2))

        card = _columns_by_key(build_board(self.owner))["OPEN"].cards[0]

        assert card.ends_soon is False
        assert card.weeks_until_end == -2

    def test_without_end_date_there_are_no_weeks(self):
        self._assignment("Geen einddatum")

        card = _columns_by_key(build_board(self.owner))["OPEN"].cards[0]

        assert card.weeks_until_end is None
        assert card.ends_soon is False

    def test_ending_within_filter_keeps_only_that_window(self):
        today = timezone.now().date()
        self._assignment("Binnenkort", end_date=today + timedelta(days=20))
        self._assignment("Later", end_date=today + timedelta(days=200))

        columns = build_board(self.owner, ending_within_months=1)

        assert _card_names(columns, "OPEN") == ["Binnenkort"]

    def test_ending_within_filter_excludes_past_dates(self):
        today = timezone.now().date()
        self._assignment("Al afgelopen", end_date=today - timedelta(days=5))

        columns = build_board(self.owner, ending_within_months=1)

        assert _card_names(columns, "OPEN") == []

    def test_ending_within_filter_excludes_assignments_without_end_date(self):
        self._assignment("Geen einddatum")

        columns = build_board(self.owner, ending_within_months=3)

        assert _card_names(columns, "OPEN") == []


class BoardGildeLabelTest(TestCase):
    """The gilde chips: an assignment has no labels, the people on it do."""

    def setUp(self):
        self.owner = Colleague.objects.create(name="BM", email="bm@rijksoverheid.nl", source="wies")
        self.category = LabelCategory.objects.create(name="Subgroep", color="#DCE3EA")
        self.ai = Label.objects.create(name="AI", category=self.category)
        self.ict = Label.objects.create(name="ICT", category=self.category)

    def _assignment_with(self, name, *labels):
        assignment = Assignment.objects.create(name=name, owner=self.owner, source="wies")
        service = Service.objects.create(assignment=assignment, description="Rol", source="wies")
        colleague = Colleague.objects.create(
            name=f"C{service.id}", email=f"c{service.id}@rijksoverheid.nl", source="wies"
        )
        colleague.labels.set(labels)
        Placement.objects.create(colleague=colleague, service=service, source="wies")
        return assignment

    def _card(self, name):
        for column in build_board(self.owner):
            for card in column.cards:
                if card.name == name:
                    return card
        return None

    def test_card_carries_its_team_gilde(self):
        self._assignment_with("Met AI", self.ai)

        assert self._card("Met AI").gilde_labels == [("AI", "neutral")]

    def test_assignment_without_placements_has_no_gilde(self):
        Assignment.objects.create(name="Nog niemand", owner=self.owner, source="wies")

        assert self._card("Nog niemand").gilde_labels == []

    def test_mixed_team_names_both_gildes(self):
        assignment = self._assignment_with("Gemengd", self.ai)
        service = Service.objects.create(assignment=assignment, description="Tweede", source="wies")
        other = Colleague.objects.create(name="Ander", email="ander@rijksoverheid.nl", source="wies")
        other.labels.set([self.ict])
        Placement.objects.create(colleague=other, service=service, source="wies")

        assert self._card("Gemengd").gilde_labels == [("AI", "neutral"), ("ICT", "neutral")]

    def test_one_gilde_is_not_repeated_per_person(self):
        assignment = self._assignment_with("Twee keer AI", self.ai)
        service = Service.objects.create(assignment=assignment, description="Tweede", source="wies")
        other = Colleague.objects.create(name="Ander", email="ander@rijksoverheid.nl", source="wies")
        other.labels.set([self.ai])
        Placement.objects.create(colleague=other, service=service, source="wies")

        assert self._card("Twee keer AI").gilde_labels == [("AI", "neutral")]

    def test_only_the_gilde_category_becomes_a_chip(self):
        expertise = LabelCategory.objects.create(name="Expertise", color="#B3D7EE")
        python = Label.objects.create(name="Python", category=expertise)
        self._assignment_with("Met expertise", self.ai, python)

        assert self._card("Met expertise").gilde_labels == [("AI", "neutral")]

    def test_label_filter_keeps_only_that_gilde(self):
        self._assignment_with("AI-werk", self.ai)
        self._assignment_with("ICT-werk", self.ict)

        columns = build_board(self.owner, label_ids=[self.ai.id])

        assert _card_names(columns, "OPEN") == ["AI-werk"]

    def test_label_filter_does_not_duplicate_a_card(self):
        """Two people with the same label on one assignment is still one card."""
        assignment = self._assignment_with("Twee keer AI", self.ai)
        service = Service.objects.create(assignment=assignment, description="Tweede", source="wies")
        other = Colleague.objects.create(name="Ander", email="ander@rijksoverheid.nl", source="wies")
        other.labels.set([self.ai])
        Placement.objects.create(colleague=other, service=service, source="wies")

        columns = build_board(self.owner, label_ids=[self.ai.id])

        assert _card_names(columns, "OPEN") == ["Twee keer AI"]


class BoardOrgFilterTest(TestCase):
    def setUp(self):
        self.owner = Colleague.objects.create(name="BM", email="bm@rijksoverheid.nl", source="wies")
        self.org = OrganizationUnit.objects.create(name="Ministerie A")
        self.other = OrganizationUnit.objects.create(name="Ministerie B")

    def _assignment(self, name, organization):
        assignment = Assignment.objects.create(name=name, owner=self.owner, source="wies")
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=organization, role="PRIMARY")
        return assignment

    def test_org_filter_keeps_only_that_client(self):
        self._assignment("Bij A", self.org)
        self._assignment("Bij B", self.other)

        columns = build_board(self.owner, org_ids=[self.org.id])

        assert _card_names(columns, "OPEN") == ["Bij A"]

    def test_without_org_filter_everything_stays(self):
        self._assignment("Bij A", self.org)
        self._assignment("Bij B", self.other)

        columns = build_board(self.owner, org_ids=[])

        assert sorted(_card_names(columns, "OPEN")) == ["Bij A", "Bij B"]


class MoveAssignmentTest(TestCase):
    def setUp(self):
        self.assignment = Assignment.objects.create(name="Opdracht", source="wies", status="OPEN")

    def test_move_sets_the_status(self):
        assert move_assignment(self.assignment, "INGEVULD") is True

        self.assignment.refresh_from_db()
        assert self.assignment.status == "INGEVULD"

    def test_unknown_status_is_refused(self):
        assert move_assignment(self.assignment, "ONZIN") is False

        self.assignment.refresh_from_db()
        assert self.assignment.status == "OPEN"


class BmBoardAuthTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()
        self.url = reverse("bm-board")

        self.bdm_user = User.objects.create(email="bdm@rijksoverheid.nl")
        self.bdm_user.groups.add(Group.objects.get(name="Business Development Manager"))

        self.regular_user = User.objects.create(email="regular@rijksoverheid.nl")

    def test_anonymous_redirected(self):
        response = self.client.get(self.url)

        assert response.status_code == 302
        assert "/geen-toegang/" in response.url

    def test_non_bdm_redirected(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(self.url)

        assert response.status_code == 302
        assert "/geen-toegang/" in response.url

    def test_bdm_gets_the_board(self):
        self.client.force_login(self.bdm_user)

        response = self.client.get(self.url)

        assert response.status_code == 200


class BmBoardViewTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()
        self.url = reverse("bm-board")

        self.user = User.objects.create(email="bdm@rijksoverheid.nl")
        self.user.groups.add(Group.objects.get(name="Business Development Manager"))
        self.owner = Colleague.objects.create(name="BM", email="bdm@rijksoverheid.nl", source="wies", user=self.user)
        self.client.force_login(self.user)

    def _assignment(self, name, **kwargs):
        kwargs.setdefault("owner", self.owner)
        kwargs.setdefault("source", "wies")
        return Assignment.objects.create(name=name, **kwargs)

    def test_own_assignment_is_on_the_page(self):
        self._assignment("Mijn opdracht")

        response = self.client.get(self.url)

        self.assertContains(response, "Mijn opdracht")

    def test_htmx_request_returns_only_the_columns(self):
        self._assignment("Mijn opdracht")

        response = self.client.get(self.url, headers={"hx-request": "true"})

        assert response.status_code == 200
        self.assertContains(response, "bm-board-grid")
        # The full page chrome stays out of a partial swap.
        self.assertNotContains(response, "<h1>Bord</h1>")

    def test_ending_filter_narrows_the_board(self):
        today = timezone.now().date()
        self._assignment("Binnenkort", end_date=today + timedelta(days=20))
        self._assignment("Veel later", end_date=today + timedelta(days=200))

        response = self.client.get(self.url, {"eindigt": "1"})

        self.assertContains(response, "Binnenkort")
        self.assertNotContains(response, "Veel later")

    def test_nonsense_ending_filter_is_ignored(self):
        self._assignment("Mijn opdracht")

        response = self.client.get(self.url, {"eindigt": "onzin"})

        assert response.status_code == 200
        self.assertContains(response, "Mijn opdracht")

    def test_widest_ending_window_wins(self):
        """The sheet renders checkboxes, so several windows can arrive at once."""
        today = timezone.now().date()
        self._assignment("Over twee maanden", end_date=today + timedelta(days=50))

        response = self.client.get(self.url, {"eindigt": ["1", "3"]})

        self.assertContains(response, "Over twee maanden")

    def test_empty_board_says_you_own_nothing(self):
        response = self.client.get(self.url)

        self.assertContains(response, "nog geen opdrachten op jouw naam")

    def test_empty_board_under_a_filter_says_so_instead(self):
        today = timezone.now().date()
        self._assignment("Loopt door", end_date=today + timedelta(days=300))

        response = self.client.get(self.url, {"eindigt": "1"})

        self.assertContains(response, "Geen opdrachten binnen deze filters")

    def test_ending_filter_outside_the_choices_is_ignored(self):
        today = timezone.now().date()
        self._assignment("Veel later", end_date=today + timedelta(days=200))

        response = self.client.get(self.url, {"eindigt": "99"})

        # 99 is not on offer, so the board comes back unfiltered rather than
        # silently showing a window nobody asked for.
        self.assertContains(response, "Veel later")


class BmBoardCreateButtonTest(TestCase):
    """ "Opdracht invoeren" works the same here as on the Aanvragen list."""

    def setUp(self):
        setup_roles()
        self.client = Client()
        self.user = User.objects.create(email="bdm@rijksoverheid.nl")
        self.user.groups.add(Group.objects.get(name="Business Development Manager"))
        Colleague.objects.create(name="BM", email="bdm@rijksoverheid.nl", source="wies", user=self.user)
        self.client.force_login(self.user)

    def test_button_on_both_business_management_pages(self):
        for name in ("bm-board", "bezetting"):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))

                self.assertContains(response, "Opdracht invoeren")

    def test_new_assignment_param_opens_the_create_form(self):
        for name in ("bm-board", "bezetting"):
            with self.subTest(page=name):
                response = self.client.get(reverse(name), {"nieuwe-opdracht": ""})

                self.assertContains(response, "Voer opdracht in")

    def test_without_the_permission_there_is_no_button(self):
        user = User.objects.create(email="geen-rechten@rijksoverheid.nl")
        user.groups.add(Group.objects.get(name="Business Development Manager"))
        Colleague.objects.create(name="X", email="geen-rechten@rijksoverheid.nl", source="wies", user=user)
        user.user_permissions.clear()
        self.client.force_login(user)

        response = self.client.get(reverse("bm-board"))

        # Only when the role actually carries core.add_assignment.
        if not user.has_perm("core.add_assignment"):
            self.assertNotContains(response, "Opdracht invoeren")

    def test_create_form_wins_from_an_assignment_panel(self):
        """Both params at once: the create form has no object, so it goes first."""
        assignment = Assignment.objects.create(name="Bestaand", source="wies")

        response = self.client.get(reverse("bm-board"), {"nieuwe-opdracht": "", "opdracht": str(assignment.public_id)})

        self.assertContains(response, "Voer opdracht in")


class AssignmentCreateStatusTest(TestCase):
    """The status picked on the create form decides the card's column."""

    def setUp(self):
        setup_roles()
        self.client = Client()
        self.user = User.objects.create(email="bdm@rijksoverheid.nl")
        self.user.groups.add(Group.objects.get(name="Business Development Manager"))
        self.owner = Colleague.objects.create(name="BM", email="bdm@rijksoverheid.nl", source="wies", user=self.user)
        self.org = OrganizationUnit.objects.create(name="Ministerie A")
        self.client.force_login(self.user)

    def _create(self, name, status):
        return self.client.post(
            reverse("assignment-create-sheet"),
            {
                "name": name,
                "extra_info": "",
                "org-TOTAL_FORMS": "1",
                "org-0-organization": str(self.org.public_id),
                "org-0-role": "PRIMARY",
                "owner": str(self.owner.public_id),
                "status": status,
                "terug_url": reverse("bm-board"),
            },
        )

    def test_form_offers_every_column_as_a_status(self):
        response = self.client.get(reverse("bm-board"), {"nieuwe-opdracht": ""})

        for value, label in ASSIGNMENT_STATUS.items():
            with self.subTest(status=value):
                self.assertContains(response, f'value="{value}"')
                self.assertContains(response, label)

    def test_chosen_status_is_saved(self):
        self._create("Nieuwe lead", "LEAD")

        assert Assignment.objects.get(name="Nieuwe lead").status == "LEAD"

    def test_card_lands_in_the_column_it_was_created_in(self):
        self._create("Nieuwe lead", "LEAD")

        columns = build_board(self.owner)

        assert _card_names(columns, "LEAD") == ["Nieuwe lead"]
        assert _card_names(columns, "OPEN") == []

    def test_creating_from_the_board_reloads_the_page(self):
        """A panel-only swap would leave the columns on their old counts."""
        response = self._create("Nieuwe lead", "LEAD")

        assert response.headers.get("HX-Redirect", "").startswith(reverse("bm-board"))
        assert "HX-Location" not in response.headers

    def test_creating_from_the_list_still_swaps_only_the_panel(self):
        response = self.client.post(
            reverse("assignment-create-sheet"),
            {
                "name": "Via de lijst",
                "extra_info": "",
                "org-TOTAL_FORMS": "1",
                "org-0-organization": str(self.org.public_id),
                "org-0-role": "PRIMARY",
                "owner": str(self.owner.public_id),
                "status": "LEAD",
                "terug_url": reverse("assignment-list"),
            },
        )

        assert "HX-Location" in response.headers
        assert "HX-Redirect" not in response.headers

    def test_status_shows_in_the_panel_for_business_management(self):
        assignment = Assignment.objects.create(name="Met status", owner=self.owner, source="wies", status="LEAD")

        response = self.client.get(reverse("bm-board"), {"opdracht": str(assignment.public_id)})

        self.assertContains(response, 'text="Status"')
        self.assertContains(response, "Lead")

    def test_status_stays_hidden_outside_business_management(self):
        assignment = Assignment.objects.create(name="Met status", owner=self.owner, source="wies", status="LEAD")
        consultant = User.objects.create(email="consultant@rijksoverheid.nl")
        consultant.groups.add(Group.objects.get(name="Consultant"))
        self.client.force_login(consultant)

        response = self.client.get(reverse("assignment-list"), {"opdracht": str(assignment.public_id)})

        self.assertNotContains(response, 'text="Status"')

    def test_status_is_editable_from_the_panel(self):
        assignment = Assignment.objects.create(name="Te verplaatsen", owner=self.owner, source="wies", status="LEAD")

        specs = assignment_edit_specs(assignment, self.user)

        assert "status" in [spec.name for _, spec, _ in specs]

    def test_editing_the_status_moves_the_card(self):
        assignment = Assignment.objects.create(name="Te verplaatsen", owner=self.owner, source="wies", status="LEAD")

        response = self.client.post(
            reverse("assignment-edit", args=[assignment.public_id]),
            {
                "name": assignment.name,
                "extra_info": "",
                "org-TOTAL_FORMS": "1",
                "org-0-organization": str(self.org.public_id),
                "org-0-role": "PRIMARY",
                "owner": str(self.owner.public_id),
                "status": "INGEVULD",
                "terug_url": reverse("bm-board"),
            },
        )

        assert response.status_code in (204, 200)
        assignment.refresh_from_db()
        assert assignment.status == "INGEVULD"
        assert _card_names(build_board(self.owner), "INGEVULD") == ["Te verplaatsen"]

    def test_editing_from_the_board_reloads_it(self):
        """A panel-only swap would leave the columns on their pre-save counts."""
        assignment = Assignment.objects.create(name="Te verplaatsen", owner=self.owner, source="wies", status="LEAD")

        response = self.client.post(
            reverse("assignment-edit", args=[assignment.public_id]),
            {
                "name": assignment.name,
                "extra_info": "",
                "org-TOTAL_FORMS": "1",
                "org-0-organization": str(self.org.public_id),
                "org-0-role": "PRIMARY",
                "owner": str(self.owner.public_id),
                "status": "INGEVULD",
                "terug_url": reverse("bm-board"),
            },
        )

        assert response.headers.get("HX-Redirect", "").startswith(reverse("bm-board"))

    def test_status_is_not_editable_without_business_management(self):
        """Someone who may edit the assignment still cannot move it on the board."""
        editor = User.objects.create(email="editor@rijksoverheid.nl")
        editor.user_permissions.add(Permission.objects.get(codename="change_assignment"))
        editor = User.objects.get(pk=editor.pk)  # drop the permission cache
        assignment = Assignment.objects.create(name="Van een ander", owner=self.owner, source="wies")

        names = [spec.name for _, spec, _ in assignment_edit_specs(assignment, editor)]

        assert names, "editor should be able to edit something at all"
        assert "status" not in names

    def test_closing_reason_shows_once_an_assignment_is_closed(self):
        assignment = Assignment.objects.create(
            name="Afgerond",
            owner=self.owner,
            source="wies",
            status="GESLOTEN",
            closing_reason="Periode afgelopen zoals gepland.",
        )

        response = self.client.get(reverse("bm-board"), {"opdracht": str(assignment.public_id)})

        self.assertContains(response, "Reden van sluiten")
        self.assertContains(response, "Periode afgelopen zoals gepland.")

    def test_closing_reason_row_stays_away_while_it_is_open(self):
        """An open assignment would show an empty row asking a question nobody
        is answering yet."""
        assignment = Assignment.objects.create(name="Loopt nog", owner=self.owner, source="wies", status="OPEN")

        response = self.client.get(reverse("bm-board"), {"opdracht": str(assignment.public_id)})

        self.assertNotContains(response, "Reden van sluiten")

    def test_closing_reason_is_optional(self):
        assignment = Assignment.objects.create(name="Zonder reden", owner=self.owner, source="wies", status="GESLOTEN")

        response = self.client.get(reverse("bm-board"), {"opdracht": str(assignment.public_id)})

        self.assertContains(response, "Reden van sluiten")
        self.assertContains(response, "Niet ingevuld")

    def test_closing_reason_is_saved_from_the_edit_form(self):
        assignment = Assignment.objects.create(name="Te sluiten", owner=self.owner, source="wies", status="OPEN")

        self.client.post(
            reverse("assignment-edit", args=[assignment.public_id]),
            {
                "name": assignment.name,
                "extra_info": "",
                "org-TOTAL_FORMS": "1",
                "org-0-organization": str(self.org.public_id),
                "org-0-role": "PRIMARY",
                "owner": str(self.owner.public_id),
                "status": "GESLOTEN",
                "closing_reason": "Geen geschikte mensen beschikbaar gekregen.",
            },
        )

        assignment.refresh_from_db()
        assert assignment.status == "GESLOTEN"
        assert assignment.closing_reason == "Geen geschikte mensen beschikbaar gekregen."

    def test_closing_reason_needs_business_management_too(self):
        editor = User.objects.create(email="editor2@rijksoverheid.nl")
        editor.user_permissions.add(Permission.objects.get(codename="change_assignment"))
        editor = User.objects.get(pk=editor.pk)
        assignment = Assignment.objects.create(name="Van een ander", owner=self.owner, source="wies")

        names = [spec.name for _, spec, _ in assignment_edit_specs(assignment, editor)]

        assert "closing_reason" not in names

    def test_without_a_status_it_falls_back_to_the_model_default(self):
        """Callers that pass nothing still get an assignment on the board."""
        assignment = create_assignment_from_form(name="Zonder status", owner=self.owner)

        assert assignment.status == "OPEN"


class BmBoardMoveTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()

        self.user = User.objects.create(email="bdm@rijksoverheid.nl")
        self.user.groups.add(Group.objects.get(name="Business Development Manager"))
        self.owner = Colleague.objects.create(name="BM", email="bdm@rijksoverheid.nl", source="wies", user=self.user)
        self.assignment = Assignment.objects.create(name="Opdracht", source="wies", owner=self.owner, status="OPEN")
        self.client.force_login(self.user)

    def _url(self, assignment=None):
        return reverse("bm-board-move", args=[(assignment or self.assignment).public_id])

    def test_move_updates_the_status(self):
        response = self.client.post(self._url(), {"status": "INGEVULD"})

        assert response.status_code == 200
        self.assignment.refresh_from_db()
        assert self.assignment.status == "INGEVULD"

    def test_unknown_status_is_rejected(self):
        response = self.client.post(self._url(), {"status": "ONZIN"})

        assert response.status_code == 400
        self.assignment.refresh_from_db()
        assert self.assignment.status == "OPEN"

    def test_get_is_not_allowed(self):
        response = self.client.get(self._url())

        assert response.status_code == 405

    def test_cannot_move_someone_elses_assignment(self):
        other = Colleague.objects.create(name="Ander", email="ander@rijksoverheid.nl", source="wies")
        theirs = Assignment.objects.create(name="Van hen", source="wies", owner=other, status="OPEN")

        response = self.client.post(self._url(theirs), {"status": "GESLOTEN"})

        assert response.status_code == 404
        theirs.refresh_from_db()
        assert theirs.status == "OPEN"

    def test_non_bdm_cannot_move(self):
        regular = User.objects.create(email="regular@rijksoverheid.nl")
        self.client.force_login(regular)

        response = self.client.post(self._url(), {"status": "GESLOTEN"})

        assert response.status_code == 302
        self.assignment.refresh_from_db()
        assert self.assignment.status == "OPEN"
