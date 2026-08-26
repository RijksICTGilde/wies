"""Tests for the 'Wie zit waar?' view modes, group pagination and cards.

Covers the ?weergave= switch (persoon/opdracht), pagination on groups instead
of placements, the card structures built per view, and the per-view sort
options.
"""

import html as html_module
import json
import re
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    Event,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
)

User = get_user_model()


def _make_assignment(name, *, source="wies"):
    """An assignment that is active today, so its placements are publicly visible."""
    today = timezone.now().date()
    return Assignment.objects.create(
        name=name,
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=30),
        source=source,
    )


def _make_colleague(name):
    return Colleague.objects.create(
        name=name,
        email=f"{name.replace(' ', '.').lower()}@rijksoverheid.nl",
        source="wies",
    )


def _log_change(assignment, when):
    """An audit event for the assignment, the source of its last-change order."""
    return Event.objects.create(
        timestamp=when, object_type="Assignment", object_id=assignment.id, action="update", source="ui"
    )


def _place(colleague, assignment, skill=None):
    """Place a colleague on an assignment through a fresh service."""
    service = Service.objects.create(
        assignment=assignment,
        description=f"Service voor {colleague.name}",
        skill=skill,
        source="wies",
    )
    return Placement.objects.create(colleague=colleague, service=service, source="wies")


def _place_for_period(colleague, assignment, start, end, skill=None):
    """Place a colleague for a period of its own, ignoring the assignment's."""
    service = Service.objects.create(
        assignment=assignment,
        description=f"Service voor {colleague.name}",
        skill=skill,
        source="wies",
    )
    return Placement.objects.create(
        colleague=colleague,
        service=service,
        period_source="PLACEMENT",
        specific_start_date=start,
        specific_end_date=end,
        source="wies",
    )


@pytest.mark.django_db
class TestActiveView:
    """The ?weergave= parameter selects the card layout."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(email="test@rijksoverheid.nl", password="testpass123")
        self.client = Client()
        self.client.force_login(self.user)

        self.skill = Skill.objects.create(name="Ontwikkelaar")
        self.assignment = _make_assignment("Cloud Migratie")
        _place(_make_colleague("Jan de Vries"), self.assignment, self.skill)

    def test_default_view_is_persoon(self):
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        assert response.context_data["active_view"] == "persoon"

    def test_opdracht_view_is_selected(self):
        response = self.client.get(reverse("home"), {"weergave": "opdracht"})
        assert response.status_code == 200
        assert response.context_data["active_view"] == "opdracht"

    @pytest.mark.parametrize("value", ["zzz", "", "PERSOON", "assignment", "1"])
    def test_unknown_weergave_falls_back_to_persoon(self, value):
        """An unknown ?weergave= must not 500; it renders the default view."""
        response = self.client.get(reverse("home"), {"weergave": value})
        assert response.status_code == 200
        assert response.context_data["active_view"] == "persoon"

    def test_view_options_mark_the_active_one_as_selected(self):
        response = self.client.get(reverse("home"), {"weergave": "opdracht"})
        selected = [option["value"] for option in response.context_data["view_options"] if option["selected"]]
        assert selected == ["opdracht"]

    def test_view_switch_url_keeps_filters_but_drops_order_and_page(self):
        """Switching view keeps the search/filter but not the view-specific sort."""
        response = self.client.get(
            reverse("home"),
            {"weergave": "opdracht", "zoek": "Cloud", "order": "-assignment", "pagina": "2"},
        )
        urls = {option["value"]: option["url"] for option in response.context_data["view_options"]}
        assert "zoek=Cloud" in urls["persoon"]
        assert "order=" not in urls["persoon"]
        assert "pagina=" not in urls["persoon"]
        assert "weergave=" not in urls["persoon"]
        assert "weergave=opdracht" in urls["opdracht"]


@pytest.mark.django_db
class TestGroupPagination:
    """Pagination runs over groups (people or assignments), never over placements."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(email="test@rijksoverheid.nl", password="testpass123")
        self.client = Client()
        self.client.force_login(self.user)
        self.skill = Skill.objects.create(name="Ontwikkelaar")

    def test_paginator_counts_people_not_placements(self):
        """Five people on two assignments each is ten placements but five cards."""
        for i in range(5):
            colleague = _make_colleague(f"Collega {i}")
            for j in range(2):
                _place(colleague, _make_assignment(f"Opdracht {i}-{j}"), self.skill)

        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        assert response.context_data["paginator"].count == 5
        assert len(response.context_data["object_list"]) == 10

    def test_paginator_counts_assignments_in_opdracht_view(self):
        """Two assignments with three team members each is six placements but two cards."""
        for i in range(2):
            assignment = _make_assignment(f"Opdracht {i}")
            for j in range(3):
                _place(_make_colleague(f"Collega {i}-{j}"), assignment, self.skill)

        response = self.client.get(reverse("home"), {"weergave": "opdracht"})
        assert response.status_code == 200
        assert response.context_data["paginator"].count == 2
        assert len(response.context_data["object_list"]) == 6

    def test_group_is_never_split_across_a_page_boundary(self):
        """Every placement of a person sits on the same page as that person's card.

        61 people (page size is 60) puts a group right at the boundary; each has
        two placements, so a naive placement-based paginator would cut one in half.
        """
        for i in range(61):
            colleague = _make_colleague(f"Collega {i:03d}")
            for j in range(2):
                _place(colleague, _make_assignment(f"Opdracht {i:03d}-{j}"), self.skill)

        page1 = self.client.get(reverse("home"))
        page2 = self.client.get(reverse("home"), {"pagina": "2"})
        assert page1.status_code == 200
        assert page2.status_code == 200

        page1_colleagues = {p.colleague_id for p in page1.context_data["object_list"]}
        page2_colleagues = {p.colleague_id for p in page2.context_data["object_list"]}

        assert len(page1_colleagues) == 60
        assert len(page2_colleagues) == 1
        assert not (page1_colleagues & page2_colleagues)

        for page in (page1, page2):
            counts = {}
            for placement in page.context_data["object_list"]:
                counts[placement.colleague_id] = counts.get(placement.colleague_id, 0) + 1
            assert set(counts.values()) == {2}

        assert len(page1.context_data["object_list"]) == 120
        assert len(page2.context_data["object_list"]) == 2

    def test_every_group_appears_exactly_once_across_pages(self):
        for i in range(61):
            _place(_make_colleague(f"Collega {i:03d}"), _make_assignment(f"Opdracht {i:03d}"), self.skill)

        seen = []
        for page_number in (1, 2):
            response = self.client.get(reverse("home"), {"pagina": str(page_number)})
            seen.extend(p.colleague_id for p in response.context_data["object_list"])

        assert len(seen) == 61
        assert len(set(seen)) == 61

    @pytest.mark.parametrize("page", ["abc", "0", "-1", "999", "", "1.5"])
    def test_nonsense_page_number_does_not_error(self, page):
        """A bad ?pagina= clamps to an existing page instead of raising."""
        _place(_make_colleague("Jan de Vries"), _make_assignment("Cloud Migratie"), self.skill)

        response = self.client.get(reverse("home"), {"pagina": page})
        assert response.status_code == 200
        assert response.context_data["page_obj"].number == 1

    def test_page_number_above_last_page_clamps_to_last(self):
        for i in range(61):
            _place(_make_colleague(f"Collega {i:03d}"), _make_assignment(f"Opdracht {i:03d}"), self.skill)

        response = self.client.get(reverse("home"), {"pagina": "500"})
        assert response.status_code == 200
        assert response.context_data["page_obj"].number == 2

    def test_empty_result_set_renders_without_error(self):
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        assert response.context_data["paginator"].count == 0
        assert response.context_data["cards"] == []


@pytest.mark.django_db
class TestPersonCards:
    """The persoon view builds one card per colleague."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(email="test@rijksoverheid.nl", password="testpass123")
        self.client = Client()
        self.client.force_login(self.user)
        self.skill = Skill.objects.create(name="Ontwikkelaar")

    def _cards(self, params=None):
        response = self.client.get(reverse("home"), params or {})
        assert response.status_code == 200
        return {card["name"]: card for card in response.context_data["cards"]}

    def test_one_card_per_colleague(self):
        colleague = _make_colleague("Jan de Vries")
        _place(colleague, _make_assignment("Opdracht A"), self.skill)
        _place(colleague, _make_assignment("Opdracht B"), self.skill)

        cards = self._cards()
        assert list(cards) == ["Jan de Vries"]
        assert len(cards["Jan de Vries"]["assignments"]) == 2

    def test_single_assignment_card_links_to_the_placement(self):
        """One assignment means one placement to show, so the panel opens it."""
        colleague = _make_colleague("Jan de Vries")
        placement = _place(colleague, _make_assignment("Cloud Migratie"), self.skill)

        card = self._cards()["Jan de Vries"]
        assert card["assignment"] is not None
        assert f"plaatsing={placement.public_id}" in card["panel_url"]
        assert "collega=" not in card["panel_url"]

    def test_multiple_assignments_card_links_to_the_colleague(self):
        """With more than one assignment there is no single placement to open."""
        colleague = _make_colleague("Jan de Vries")
        _place(colleague, _make_assignment("Opdracht A"), self.skill)
        _place(colleague, _make_assignment("Opdracht B"), self.skill)

        card = self._cards()["Jan de Vries"]
        assert card["assignment"] is None
        assert f"collega={colleague.public_id}" in card["panel_url"]
        assert "plaatsing=" not in card["panel_url"]

    def test_roles_are_deduplicated(self):
        """Two placements with the same skill list that role once."""
        colleague = _make_colleague("Jan de Vries")
        tester = Skill.objects.create(name="Tester")
        _place(colleague, _make_assignment("Opdracht A"), self.skill)
        _place(colleague, _make_assignment("Opdracht B"), self.skill)
        _place(colleague, _make_assignment("Opdracht C"), tester)

        roles = self._cards()["Jan de Vries"]["roles"]
        assert sorted(roles) == ["Ontwikkelaar", "Tester"]

    def test_placement_without_skill_adds_no_role(self):
        colleague = _make_colleague("Jan de Vries")
        _place(colleague, _make_assignment("Opdracht A"), None)

        assert self._cards()["Jan de Vries"]["roles"] == []


@pytest.mark.django_db
class TestAssignmentCards:
    """The opdracht view builds one card per assignment, with the full team."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(email="test@rijksoverheid.nl", password="testpass123")
        self.client = Client()
        self.client.force_login(self.user)
        self.developer = Skill.objects.create(name="Ontwikkelaar")
        self.tester = Skill.objects.create(name="Tester")

    def _cards(self, params=None):
        response = self.client.get(reverse("home"), {"weergave": "opdracht", **(params or {})})
        assert response.status_code == 200
        return {card["name"]: card for card in response.context_data["cards"]}

    def test_one_card_per_assignment_with_full_team(self):
        assignment = _make_assignment("Cloud Migratie")
        _place(_make_colleague("Anna Bakker"), assignment, self.developer)
        _place(_make_colleague("Jan de Vries"), assignment, self.tester)

        cards = self._cards()
        assert list(cards) == ["Cloud Migratie"]
        assert cards["Cloud Migratie"]["team"] == [
            {"name": "Anna Bakker", "role": "Ontwikkelaar"},
            {"name": "Jan de Vries", "role": "Tester"},
        ]

    def test_team_shows_everyone_despite_an_active_role_filter(self):
        """A role filter narrows which cards show, not who is on the team.

        Filtering on Tester leaves only Jan's placement, but the card is about the
        assignment: hiding Anna would misrepresent the team.
        """
        assignment = _make_assignment("Cloud Migratie")
        _place(_make_colleague("Anna Bakker"), assignment, self.developer)
        _place(_make_colleague("Jan de Vries"), assignment, self.tester)

        cards = self._cards({"rol": str(self.tester.public_id)})
        assert list(cards) == ["Cloud Migratie"]

        team_names = [member["name"] for member in cards["Cloud Migratie"]["team"]]
        assert team_names == ["Anna Bakker", "Jan de Vries"]

    def test_role_filter_still_excludes_assignments_without_a_match(self):
        matching = _make_assignment("Cloud Migratie")
        _place(_make_colleague("Jan de Vries"), matching, self.tester)

        other = _make_assignment("Datawarehouse")
        _place(_make_colleague("Anna Bakker"), other, self.developer)

        assert list(self._cards({"rol": str(self.tester.public_id)})) == ["Cloud Migratie"]

    def test_team_member_listed_once_when_placed_twice(self):
        """Two services on one assignment for the same person is still one team row."""
        assignment = _make_assignment("Cloud Migratie")
        colleague = _make_colleague("Jan de Vries")
        _place(colleague, assignment, self.developer)
        _place(colleague, assignment, self.tester)

        team = self._cards()["Cloud Migratie"]["team"]
        assert [member["name"] for member in team] == ["Jan de Vries"]

    def test_card_links_to_the_assignment_panel(self):
        assignment = _make_assignment("Cloud Migratie")
        _place(_make_colleague("Jan de Vries"), assignment, self.developer)

        card = self._cards()["Cloud Migratie"]
        assert f"opdracht={assignment.public_id}" in card["panel_url"]

    def test_team_leaves_out_ended_and_future_placements(self):
        """The team is the team as it stands today, like the list itself.

        Sidestepping the selection filters is deliberate; sidestepping the
        visibility filter is not. Without it the card names people who left
        months ago or have not started yet.
        """
        today = timezone.now().date()
        assignment = _make_assignment("Cloud Migratie")
        _place(_make_colleague("Actief Persoon"), assignment, self.developer)
        _place_for_period(
            _make_colleague("Oud Teamlid"),
            assignment,
            today - timedelta(days=400),
            today - timedelta(days=200),
            self.developer,
        )
        _place_for_period(
            _make_colleague("Toekomstig Teamlid"),
            assignment,
            today + timedelta(days=10),
            today + timedelta(days=100),
            self.developer,
        )

        team = self._cards()["Cloud Migratie"]["team"]
        assert [member["name"] for member in team] == ["Actief Persoon"]


@pytest.mark.django_db
class TestFilterCounts:
    """Sidebar counts follow the view, so every number on screen counts the same."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(email="counts2@rijksoverheid.nl", password="testpass123")
        self.client = Client()
        self.client.force_login(self.user)
        self.skill = Skill.objects.create(name="Data engineering")

    def _rol_counts(self, params=None):
        response = self.client.get(reverse("home"), params or {})
        for group in response.context_data["filter_groups"]:
            if group["name"] == "rol":
                return {o["label"]: o["count"] for o in group["options"] if o.get("label")}
        return {}

    def test_role_count_follows_the_active_view(self):
        """Two people on one assignment: 2 in the persoon view, 1 in the opdracht view."""
        shared = _make_assignment("Gedeelde opdracht")
        _place(_make_colleague("Anna Bakker"), shared, self.skill)
        _place(_make_colleague("Bob Smit"), shared, self.skill)

        assert self._rol_counts()["Data engineering"] == 2
        assert self._rol_counts({"weergave": "opdracht"})["Data engineering"] == 1

    def test_the_count_matches_the_cards_you_get(self):
        shared = _make_assignment("Gedeelde opdracht")
        _place(_make_colleague("Anna Bakker"), shared, self.skill)
        _place(_make_colleague("Bob Smit"), shared, self.skill)
        skill_id = str(self.skill.public_id)

        for view, expected in (("persoon", 2), ("opdracht", 1)):
            params = {"weergave": view} if view != "persoon" else {}
            assert self._rol_counts(params)["Data engineering"] == expected
            response = self.client.get(reverse("home"), {**params, "rol": skill_id})
            assert response.context_data["paginator"].count == expected

    def _loopt_af_counts(self, params=None):
        response = self.client.get(reverse("home"), params or {})
        for group in response.context_data["filter_groups"]:
            if group["name"] == "loopt_af":
                return {o["label"]: o["count"] for o in group["options"] if o.get("label")}
        return {}

    def test_loopt_af_count_follows_the_active_view(self):
        """Two people on one assignment: 2 cards in persoon, 1 in opdracht."""
        shared = _make_assignment("Gedeelde opdracht")
        _place(_make_colleague("Anna Bakker"), shared, self.skill)
        _place(_make_colleague("Bob Smit"), shared, self.skill)

        assert self._loopt_af_counts()["Binnen 3 maanden"] == 2
        assert self._loopt_af_counts({"weergave": "opdracht"})["Binnen 3 maanden"] == 1

    def test_loopt_af_count_matches_the_cards_you_get(self):
        shared = _make_assignment("Gedeelde opdracht")
        _place(_make_colleague("Anna Bakker"), shared, self.skill)
        _place(_make_colleague("Bob Smit"), shared, self.skill)

        for view, expected in (("persoon", 2), ("opdracht", 1)):
            params = {"weergave": view} if view != "persoon" else {}
            assert self._loopt_af_counts(params)["Binnen 3 maanden"] == expected
            response = self.client.get(reverse("home"), {**params, "loopt_af": "3m"})
            assert response.context_data["paginator"].count == expected


@pytest.mark.django_db
class TestViewSwitch:
    """The switch carries both counts and the filter form keeps the view."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(email="counts@rijksoverheid.nl", password="testpass123")
        self.client = Client()
        self.client.force_login(self.user)
        self.skill = Skill.objects.create(name="Data engineering")

    def _counts(self, params=None):
        response = self.client.get(reverse("home"), params or {})
        return {o["value"]: o["count"] for o in response.context_data["view_options"]}

    def test_counts_group_per_view(self):
        shared = _make_assignment("Gedeelde opdracht")
        _place(_make_colleague("Anna Bakker"), shared, self.skill)
        _place(_make_colleague("Bob Smit"), shared, self.skill)
        _place(_make_colleague("Carla Jansen"), _make_assignment("Eigen opdracht"), self.skill)

        assert self._counts() == {"persoon": 3, "opdracht": 2}

    def test_counts_are_the_same_in_both_views(self):
        shared = _make_assignment("Gedeelde opdracht")
        _place(_make_colleague("Anna Bakker"), shared, self.skill)
        _place(_make_colleague("Bob Smit"), shared, self.skill)

        assert self._counts() == self._counts({"weergave": "opdracht"})

    def test_counts_follow_the_filters(self):
        _place(_make_colleague("Anna Bakker"), _make_assignment("Datateam"), self.skill)
        _place(_make_colleague("Bob Smit"), _make_assignment("Iets anders"), self.skill)

        assert self._counts({"zoek": "Datateam"}) == {"persoon": 1, "opdracht": 1}

    def test_the_filter_form_carries_the_active_view(self):
        """A filter change must not throw you back to the persoon view (#618)."""
        _place(_make_colleague("Anna Bakker"), _make_assignment("Datateam"), self.skill)

        html = self.client.get(reverse("home"), {"weergave": "opdracht"}).content.decode()
        assert 'name="weergave"' in html
        assert 'value="opdracht"' in html

        # The default view leaves the parameter out, to keep the url clean.
        assert 'name="weergave"' not in self.client.get(reverse("home")).content.decode()


@pytest.mark.django_db
class TestSortOptions:
    """Sort options and default ordering differ per view."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(email="test@rijksoverheid.nl", password="testpass123")
        self.client = Client()
        self.client.force_login(self.user)
        self.skill = Skill.objects.create(name="Ontwikkelaar")

    def _card_names(self, params=None):
        response = self.client.get(reverse("home"), params or {})
        assert response.status_code == 200
        return [card["name"] for card in response.context_data["cards"]]

    def _sort_values(self, params=None):
        response = self.client.get(reverse("home"), params or {})
        return [option["value"] for option in response.context_data["sort_options"]]

    def test_person_view_offers_name_descending(self):
        assert "-name" in self._sort_values()

    def test_assignment_view_does_not_offer_name_descending(self):
        """Sorting a team card on colleague name says nothing, so the option is gone."""
        assert "-name" not in self._sort_values({"weergave": "opdracht"})

    def test_every_sort_option_carries_its_label(self):
        """Value and label travel together, so the template cannot drift from the view."""
        response = self.client.get(reverse("home"))
        options = response.context_data["sort_options"]
        assert all(option["label"] for option in options)
        assert response.context_data["active_sort_label"] == response.context_data["default_sort_label"]

    def test_active_order_is_echoed_when_valid(self):
        response = self.client.get(reverse("home"), {"order": "-name"})
        assert response.context_data["active_order"] == "-name"

    @pytest.mark.parametrize(
        ("params", "expected_view"),
        [
            ({"weergave": "opdracht", "order": "-name"}, "opdracht"),
            ({"order": "zzz"}, "persoon"),
            # ?order=skill is gone; an old bookmark must not break.
            ({"order": "skill"}, "persoon"),
            ({"order": ""}, "persoon"),
        ],
    )
    def test_order_not_valid_for_the_view_is_ignored(self, params, expected_view):
        response = self.client.get(reverse("home"), params)
        assert response.status_code == 200
        assert response.context_data["active_view"] == expected_view
        assert response.context_data["active_order"] == ""

    def test_person_view_defaults_to_newest_start_date(self):
        """The most recently started placement leads, whatever the entry order."""
        today = timezone.now().date()
        for name, days_ago in (("Carla Jansen", 5), ("Anna Bakker", 40), ("Bob Smit", 1)):
            assignment = _make_assignment(f"Opdracht {name}")
            assignment.start_date = today - timedelta(days=days_ago)
            assignment.save(update_fields=["start_date"])
            _place(_make_colleague(name), assignment, self.skill)

        assert self._card_names() == ["Bob Smit", "Carla Jansen", "Anna Bakker"]

    def test_person_without_a_start_date_sorts_last(self):
        dated = _make_assignment("Met startdatum")
        dated.start_date = timezone.now().date() - timedelta(days=90)
        dated.save(update_fields=["start_date"])
        _place(_make_colleague("Anna Bakker"), dated, self.skill)
        undated = _make_assignment("Zonder startdatum")
        undated.start_date = None
        undated.save(update_fields=["start_date"])
        _place(_make_colleague("Bob Smit"), undated, self.skill)

        assert self._card_names() == ["Anna Bakker", "Bob Smit"]

    def test_a_newer_placement_lifts_an_existing_person_to_the_top(self):
        """A card ranks on its most recent placement, not on its oldest."""
        today = timezone.now().date()
        anna = _make_colleague("Anna Bakker")
        old = _make_assignment("Eerste opdracht")
        old.start_date = today - timedelta(days=60)
        old.save(update_fields=["start_date"])
        _place(anna, old, self.skill)

        bob_assignment = _make_assignment("Opdracht Bob")
        bob_assignment.start_date = today - timedelta(days=30)
        bob_assignment.save(update_fields=["start_date"])
        _place(_make_colleague("Bob Smit"), bob_assignment, self.skill)
        assert self._card_names() == ["Bob Smit", "Anna Bakker"]

        recent = _make_assignment("Tweede opdracht")
        recent.start_date = today - timedelta(days=2)
        recent.save(update_fields=["start_date"])
        _place(anna, recent, self.skill)
        assert self._card_names() == ["Anna Bakker", "Bob Smit"]

    def test_person_view_name_ascending_sorts_on_name(self):
        for name in ("Carla Jansen", "Anna Bakker", "Bob Smit"):
            _place(_make_colleague(name), _make_assignment(f"Opdracht {name}"), self.skill)

        assert self._card_names({"order": "name"}) == ["Anna Bakker", "Bob Smit", "Carla Jansen"]

    def test_person_view_name_descending_reverses_the_order(self):
        for name in ("Carla Jansen", "Anna Bakker", "Bob Smit"):
            _place(_make_colleague(name), _make_assignment(f"Opdracht {name}"), self.skill)

        assert self._card_names({"order": "-name"}) == ["Carla Jansen", "Bob Smit", "Anna Bakker"]

    def test_assignment_view_defaults_to_last_changed(self):
        """An opdracht ranks on its last audited change, not on when it was created."""
        now = timezone.now()
        made = {}
        for name in ("Chatbot", "Anonimisering", "Bouwportaal"):
            assignment = _make_assignment(name)
            made[name] = assignment
            _place(_make_colleague(f"Collega {name}"), assignment, self.skill)
        _log_change(made["Anonimisering"], now - timedelta(days=2))
        _log_change(made["Bouwportaal"], now - timedelta(days=1))
        _log_change(made["Chatbot"], now)

        assert self._card_names({"weergave": "opdracht"}) == ["Chatbot", "Bouwportaal", "Anonimisering"]

    def test_assignment_without_audit_events_sorts_last(self):
        """Events age out of retention; an opdracht without any must not lead."""
        changed = _make_assignment("Met wijziging")
        _place(_make_colleague("Collega A"), changed, self.skill)
        silent = _make_assignment("Zonder wijziging")
        _place(_make_colleague("Collega B"), silent, self.skill)
        _log_change(changed, timezone.now() - timedelta(days=30))

        assert self._card_names({"weergave": "opdracht"}) == ["Met wijziging", "Zonder wijziging"]

    def test_invalid_order_falls_back_to_the_view_default(self):
        """?order=-name does not exist in the opdracht view, so the default applies."""
        for name in ("Chatbot", "Anonimisering", "Bouwportaal"):
            _place(_make_colleague(f"Collega {name}"), _make_assignment(name), self.skill)

        names = self._card_names({"weergave": "opdracht", "order": "-name"})
        assert names == ["Chatbot", "Anonimisering", "Bouwportaal"]

    def test_assignment_descending_sorts_the_assignment_cards(self):
        for name in ("Chatbot", "Anonimisering", "Bouwportaal"):
            _place(_make_colleague(f"Collega {name}"), _make_assignment(name), self.skill)

        names = self._card_names({"weergave": "opdracht", "order": "-assignment"})
        assert names == ["Chatbot", "Bouwportaal", "Anonimisering"]


@pytest.mark.django_db
class TestClientModalCounts:
    """The opdrachtgever modal counts the same groups the sidebar does."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(email="modal@rijksoverheid.nl", password="testpass123")
        self.client = Client()
        self.client.force_login(self.user)
        self.skill = Skill.objects.create(name="Data engineering")
        self.org = OrganizationUnit.objects.create(name="Ministerie van Testzaken")

    def _org_count(self, params=None):
        """The org's count as the modal renders it.

        Read back out of the json_script payload: these templates are Jinja2, so
        there is no response.context to inspect.
        """
        response = self.client.get("/client-modal/", {"count_mode": "placements", "ndd": "1", **(params or {})})
        assert response.status_code == 200
        html = response.content.decode()
        raw = html.split('<script id="client-data" type="application/json">')[1].split("</script>")[0]

        def walk(nodes):
            for node in nodes:
                if node["id"] == str(self.org.public_id):
                    return node["nr_of_placements"]
                found = walk(node.get("children", []))
                if found is not None:
                    return found
            return None

        return walk(json.loads(html_module.unescape(raw)))

    def test_modal_count_follows_the_active_view(self):
        """Two colleagues on one assignment: 2 cards in persoon, 1 in opdracht.

        The modal sits next to the sidebar, which already counted groups, so a
        modal counting placements showed a number the sidebar contradicted.
        """
        shared = _make_assignment("Gedeelde opdracht")
        AssignmentOrganizationUnit.objects.create(assignment=shared, organization=self.org)
        _place(_make_colleague("Anna Bakker"), shared, self.skill)
        _place(_make_colleague("Bob Smit"), shared, self.skill)

        assert self._org_count() == 2
        assert self._org_count({"weergave": "opdracht"}) == 1


@pytest.mark.django_db
class TestActiveShape:
    """The ?vorm= parameter picks kaarten or lijst, independent of the weergave."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(email="vorm@rijksoverheid.nl", password="testpass123")
        self.client = Client()
        self.client.force_login(self.user)

        self.skill = Skill.objects.create(name="Ontwikkelaar")
        self.assignment = _make_assignment("Cloud Migratie")
        _place(_make_colleague("Jan de Vries"), self.assignment, self.skill)

    def test_default_shape_is_kaarten(self):
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        assert response.context_data["active_shape"] == "kaarten"

    def test_lijst_shape_is_selected(self):
        response = self.client.get(reverse("home"), {"vorm": "lijst"})
        assert response.status_code == 200
        assert response.context_data["active_shape"] == "lijst"

    @pytest.mark.parametrize("value", ["zzz", "", "LIJST", "list", "1"])
    def test_unknown_vorm_falls_back_to_kaarten(self, value):
        """An unknown ?vorm= must not 500; it renders the default shape."""
        response = self.client.get(reverse("home"), {"vorm": value})
        assert response.status_code == 200
        assert response.context_data["active_shape"] == "kaarten"

    def test_shape_options_mark_the_active_one_as_selected(self):
        response = self.client.get(reverse("home"), {"vorm": "lijst"})
        selected = [option["value"] for option in response.context_data["shape_options"] if option["selected"]]
        assert selected == ["lijst"]

    def test_shape_switch_url_keeps_view_search_and_order(self):
        """Both shapes show the same groups in the same order, so nothing is dropped."""
        response = self.client.get(
            reverse("home"),
            {"vorm": "lijst", "weergave": "opdracht", "zoek": "Cloud", "order": "-assignment", "pagina": "2"},
        )
        urls = {option["value"]: option["url"] for option in response.context_data["shape_options"]}
        for url in urls.values():
            assert "weergave=opdracht" in url
            assert "zoek=Cloud" in url
            assert "order=-assignment" in url
            # The two shapes fit a different number of items, so paging restarts.
            assert "pagina=" not in url
        # Explicit on both, so the link is never a no-op for a visitor whose
        # session holds the other shape.
        assert "vorm=kaarten" in urls["kaarten"]
        assert "vorm=lijst" in urls["lijst"]

    @pytest.mark.parametrize("view", ["persoon", "opdracht"])
    @pytest.mark.parametrize("shape", ["kaarten", "lijst"])
    def test_every_combination_renders(self, view, shape):
        """Weergave and vorm are independent axes: all four combinations are valid."""
        response = self.client.get(reverse("home"), {"weergave": view, "vorm": shape})
        assert response.status_code == 200
        assert response.context_data["active_view"] == view
        assert response.context_data["active_shape"] == shape
        content = response.content.decode()
        assert "Jan de Vries" in content or "Cloud Migratie" in content

    def test_lijst_renders_a_list_and_kaarten_a_collection(self):
        lijst = self.client.get(reverse("home"), {"vorm": "lijst"}).content.decode()
        assert '<nldd-list id="placement-list"' in lijst
        assert "<nldd-collection" not in lijst

        kaarten = self.client.get(reverse("home"), {"vorm": "kaarten"}).content.decode()
        assert '<nldd-collection id="placement-list"' in kaarten

    def test_opdracht_row_lets_the_text_cell_take_the_leftover_width(self):
        """A capped text cell bunches every following cell up against it.

        nldd-text-cell defaults to width="full" and is the only growing cell in
        the row, so it is what pushes the chevron to the right edge. Capping it
        (as the person view does for its first of two text columns) left the
        avatars and the chevron huddled in the left half of the row.
        """
        content = self.client.get(reverse("home"), {"vorm": "lijst", "weergave": "opdracht"}).content.decode()
        row = re.search(r"<nldd-list-item href.*?</nldd-list-item>", content, re.S).group(0)
        text_cell = re.search(r"<nldd-text-cell[^>]*>", row).group(0)
        assert "max-width" not in text_cell

    def test_opdracht_row_stacks_the_team_in_an_avatar_group(self):
        """Loose avatars in a wrap container stacked vertically and blew up the row height."""
        content = self.client.get(reverse("home"), {"vorm": "lijst", "weergave": "opdracht"}).content.decode()
        row = re.search(r"<nldd-list-item href.*?</nldd-list-item>", content, re.S).group(0)
        assert "<nldd-avatar-group" in row
        # The group itself caps what it shows and gives the rest a popover, so the
        # template must not slice the team or add a +N tag of its own.
        assert 'max="5"' in row
        assert "<nldd-tag" not in row

    def test_opdracht_row_ends_with_the_chevron(self):
        """The chevron is the last cell; anything after it would sit right of it."""
        content = self.client.get(reverse("home"), {"vorm": "lijst", "weergave": "opdracht"}).content.decode()
        row = re.search(r"<nldd-list-item href.*?</nldd-list-item>", content, re.S).group(0)
        cells = re.findall(r"<nldd-(\w+)-cell|<nldd-(cell)", row)
        last = [a or b for a, b in cells][-1]
        assert last == "icon"

    def test_empty_result_shows_one_inline_dialog_in_both_shapes(self):
        """The empty state is shared: it says the same thing whatever the shape."""
        for shape in ("kaarten", "lijst"):
            response = self.client.get(reverse("home"), {"vorm": shape, "zoek": "bestaat-niet-xyz"})
            content = response.content.decode()
            assert '<nldd-inline-dialog id="placement-list"' in content
            assert "<nldd-collection" not in content


@pytest.mark.django_db
class TestShapeIsRemembered:
    """An explicit vorm outlives the url; a shared link still wins over it."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(email="onthoud@rijksoverheid.nl", password="testpass123")
        self.client = Client()
        self.client.force_login(self.user)
        _place(_make_colleague("Jan de Vries"), _make_assignment("Cloud Migratie"))

    def test_choice_is_remembered_on_a_later_visit(self):
        self.client.get(reverse("home"), {"vorm": "lijst"})
        response = self.client.get(reverse("home"))
        assert response.context_data["active_shape"] == "lijst"

    def test_parameter_beats_the_stored_preference(self):
        """A shared ?vorm= link shows what it says, not the recipient's own default."""
        self.client.get(reverse("home"), {"vorm": "lijst"})
        response = self.client.get(reverse("home"), {"vorm": "kaarten"})
        assert response.context_data["active_shape"] == "kaarten"
        # ...and that explicit choice replaces the stored one.
        assert self.client.get(reverse("home")).context_data["active_shape"] == "kaarten"

    def test_a_bare_visit_does_not_overwrite_the_stored_preference(self):
        """The fallback value must not be written back over an explicit choice."""
        self.client.get(reverse("home"), {"vorm": "lijst"})
        self.client.get(reverse("home"))
        assert self.client.get(reverse("home")).context_data["active_shape"] == "lijst"

    def test_an_unknown_vorm_does_not_overwrite_the_stored_preference(self):
        self.client.get(reverse("home"), {"vorm": "lijst"})
        self.client.get(reverse("home"), {"vorm": "zzz"})
        assert self.client.get(reverse("home")).context_data["active_shape"] == "lijst"

    def test_the_preference_is_per_session(self):
        """Another visitor keeps the default; the preference is not global."""
        self.client.get(reverse("home"), {"vorm": "lijst"})

        other_user = User.objects.create_user(email="ander@rijksoverheid.nl", password="testpass123")
        other = Client()
        other.force_login(other_user)
        assert other.get(reverse("home")).context_data["active_shape"] == "kaarten"


@pytest.mark.django_db
class TestShapeHtmxFragments:
    """The htmx paths render the right fragment and keep the controls in sync."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(email="htmx@rijksoverheid.nl", password="testpass123")
        self.client = Client()
        self.client.force_login(self.user)
        self.assignment = _make_assignment("Cloud Migratie")
        _place(_make_colleague("Jan de Vries"), self.assignment)

    def test_paginated_fragment_follows_the_shape(self):
        """?pagina= returns bare rows in lijst and bare cards in kaarten."""
        lijst = self.client.get(
            reverse("home"), {"vorm": "lijst", "pagina": "1"}, headers={"HX-Request": "true"}
        ).content.decode()
        assert "<nldd-list-item" in lijst
        assert "<nldd-card" not in lijst

        kaarten = self.client.get(
            reverse("home"), {"vorm": "kaarten", "pagina": "1"}, headers={"HX-Request": "true"}
        ).content.decode()
        assert "<nldd-card" in kaarten

    def test_filter_swap_carries_the_shape_control_oob(self):
        """The pressed button must follow a filter change, like the other controls."""
        content = self.client.get(reverse("home"), {"vorm": "lijst"}, headers={"HX-Request": "true"}).content.decode()
        assert 'id="shape-control"' in content
        assert 'hx-swap-oob="outerHTML"' in content
        # The list itself is swapped OOB too, so both stay in sync.
        assert '<nldd-list id="placement-list"' in content

    def test_sidebar_form_carries_the_shape_so_filtering_keeps_it(self):
        """Always sent, also for the default: the session may hold the other shape."""
        for shape in ("kaarten", "lijst"):
            content = self.client.get(reverse("home"), {"vorm": shape}, headers={"HX-Request": "true"}).content.decode()
            assert 'name="vorm"' in content
            assert f'value="{shape}"' in content


@pytest.mark.django_db
class TestPersonLabels:
    """What a person card/row says about their assignments and period."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(email="labels@rijksoverheid.nl", password="testpass123")
        self.client = Client()
        self.client.force_login(self.user)
        self.colleague = _make_colleague("Kevin Popov")

    def _card(self, **params):
        response = self.client.get(reverse("home"), params)
        cards = response.context_data["cards"]
        return next(card for card in cards if card["name"] == "Kevin Popov")

    def test_one_assignment_is_named_with_its_own_end_date(self):
        _place(self.colleague, _make_assignment("Open Data Architectuur"))
        card = self._card()
        assert [line["name"] for line in card["assignment_lines"]] == ["Open Data Architectuur"]
        assert card["assignment_lines"][0]["period"].startswith("tot ")
        assert card["assignment_overflow"] == ""

    def test_two_assignments_are_both_named(self):
        """A bare count named neither, so the panel had to be opened to learn anything."""
        _place(self.colleague, _make_assignment("Open Data"))
        _place(self.colleague, _make_assignment("Burgerzaken"))
        card = self._card()
        assert sorted(line["name"] for line in card["assignment_lines"]) == ["Burgerzaken", "Open Data"]
        assert card["assignment_overflow"] == ""

    def test_names_stay_separate_values_rather_than_one_joined_string(self):
        """ "A en B" read as one long name: names carry spaces and their own "en"."""
        _place(self.colleague, _make_assignment("Vergunningen en Toezicht"))
        _place(self.colleague, _make_assignment("Open Data"))
        names = [line["name"] for line in self._card()["assignment_lines"]]
        assert len(names) == 2
        assert "Vergunningen en Toezicht" in names

    def test_every_assignment_carries_its_own_end_date(self):
        """One date under two names said nothing about which one it belonged to."""
        today = timezone.now().date()
        early = _make_assignment("Loopt eerst af")
        late = _make_assignment("Loopt later af")
        _place_for_period(self.colleague, early, today - timedelta(days=10), today + timedelta(days=30))
        _place_for_period(self.colleague, late, today - timedelta(days=10), today + timedelta(days=200))

        lines = self._card()["assignment_lines"]
        periods = {line["name"]: line["period"] for line in lines}
        assert periods["Loopt eerst af"] == f"tot {date_format(today + timedelta(days=30), 'b Y')}"
        assert periods["Loopt later af"] == f"tot {date_format(today + timedelta(days=200), 'b Y')}"

    def test_lines_are_sorted_by_end_date_soonest_first(self):
        """What frees up next leads."""
        today = timezone.now().date()
        for name, days in (("Later", 200), ("Eerder", 30), ("Middenin", 100)):
            _place_for_period(
                self.colleague, _make_assignment(name), today - timedelta(days=10), today + timedelta(days=days)
            )
        names = [line["name"] for line in self._card()["assignment_lines"]]
        assert names == ["Eerder", "Middenin"]

    def test_an_assignment_without_an_end_date_sorts_last_and_says_so(self):
        """A missing date says nothing about how soon it ends, so it must not lead."""
        today = timezone.now().date()
        open_ended = _make_assignment("Zonder einde")
        open_ended.end_date = None
        open_ended.save()
        _place(self.colleague, open_ended)
        _place_for_period(
            self.colleague, _make_assignment("Met einde"), today - timedelta(days=10), today + timedelta(days=30)
        )

        lines = self._card()["assignment_lines"]
        assert [line["name"] for line in lines] == ["Met einde", "Zonder einde"]
        assert lines[1]["period"] == "Geen einddatum"

    def test_the_end_date_respects_a_placement_specific_period(self):
        """actual_end_date, not assignment.end_date: a placement may end sooner."""
        today = timezone.now().date()
        assignment = _make_assignment("Lange opdracht")
        assignment.end_date = today + timedelta(days=300)
        assignment.save()
        _place_for_period(self.colleague, assignment, today - timedelta(days=10), today + timedelta(days=20))

        line = self._card()["assignment_lines"][0]
        assert line["period"] == f"tot {date_format(today + timedelta(days=20), 'b Y')}"

    def test_more_than_two_assignments_name_two_and_count_the_rest(self):
        """The cell must not grow without bound, so only the first two are named."""
        today = timezone.now().date()
        for i, name in enumerate(("Alpha", "Beta", "Gamma", "Delta")):
            _place_for_period(
                self.colleague,
                _make_assignment(name),
                today - timedelta(days=10),
                today + timedelta(days=30 + i * 10),
            )
        card = self._card()
        assert len(card["assignment_lines"]) == 2
        assert card["assignment_overflow"] == "+2 andere opdrachten"

    def test_a_single_hidden_assignment_is_singular(self):
        for name in ("Alpha", "Beta", "Gamma"):
            _place(self.colleague, _make_assignment(name))
        assert self._card()["assignment_overflow"] == "+1 andere opdracht"

    def test_the_inline_period_is_bracketed_and_lowercased(self):
        """Behind a name on one line, colour alone read as part of the sentence."""
        _place(self.colleague, _make_assignment("Open Data"))
        line = self._card()["assignment_lines"][0]
        assert line["period"].startswith("tot ")
        assert line["period_inline"] == f"({line['period']})"

    def test_a_missing_end_date_reads_as_a_phrase_inline(self):
        """ "(Geen einddatum)" mid-sentence would start a capital out of nowhere."""
        assignment = _make_assignment("Zonder einde")
        assignment.end_date = None
        assignment.save()
        _place(self.colleague, assignment)
        line = self._card()["assignment_lines"][0]
        assert line["period"] == "Geen einddatum"
        assert line["period_inline"] == "(geen einddatum)"

    @pytest.mark.parametrize("shape", ["kaarten", "lijst"])
    def test_both_shapes_show_the_same_labels(self, shape):
        """The labels come from the view, so a card and a row cannot drift apart."""
        _place(self.colleague, _make_assignment("Open Data"))
        _place(self.colleague, _make_assignment("Burgerzaken"))
        card = self._card(vorm=shape)
        content = self.client.get(reverse("home"), {"vorm": shape}).content.decode()
        # The row brackets the date behind the name; the card gives it its own line.
        key = "period_inline" if shape == "lijst" else "period"
        for line in card["assignment_lines"]:
            assert html_module.escape(line["name"]) in content
            assert html_module.escape(line[key]) in content
