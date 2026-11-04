"""Colleagues with an account but no current placement on "Wie zit waar?" (#778).

They follow the placed colleagues in the person view as a "Nu geen opdracht" card,
so a new account can find itself. Covers who is in that tail, how the filters,
sorting, pagination and counts treat it, the card it gets, and what each role
sees behind it in the panel.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    Label,
    LabelCategory,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
    Suborganization,
)
from wies.core.roles import ROLE_USER_ADMIN
from wies.core.tests.role_helpers import STAFF_EMAIL, grant_business_manager, grant_consultant

User = get_user_model()


def _assignment(name, *, start_days=-30, end_days=30, owner=None, org=None):
    today = timezone.now().date()
    assignment = Assignment.objects.create(
        name=name,
        start_date=today + timedelta(days=start_days),
        end_date=today + timedelta(days=end_days),
        owner=owner,
        source="wies",
    )
    if org is not None:
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=org, role="PRIMARY")
    return assignment


def _place(colleague, assignment, skill=None):
    service = Service.objects.create(assignment=assignment, description="Rol", skill=skill, source="wies")
    return Placement.objects.create(colleague=colleague, service=service, source="wies")


def _account(name, **colleague_fields):
    """A colleague with a user account, the way a login leaves one."""
    email = f"{name.replace(' ', '.').lower()}@rijksoverheid.nl"
    user = User.objects.create_user(email=email)
    return Colleague.objects.create(name=name, email=email, source="wies", user=user, **colleague_fields)


def _without_account(name):
    return Colleague.objects.create(name=name, email=f"{name.lower()}@rijksoverheid.nl", source="wies")


@pytest.fixture
def viewer_client(db):
    """A logged-in viewer named so they sort last and match no test search."""
    user = User.objects.create_user(email="kijker@rijksoverheid.nl", first_name="Zeno", last_name="Kijker")
    client = Client()
    client.force_login(user)
    return client


def _cards(client, params=None):
    response = client.get(reverse("home"), params or {})
    assert response.status_code == 200
    return response.context_data["cards"]


def _names(client, params=None):
    return [card["name"] for card in _cards(client, params)]


@pytest.mark.django_db
class TestWhoIsInTheTail:
    def test_account_without_any_placement_gets_a_card(self, viewer_client):
        _account("Anna Nieuw")
        assert "Anna Nieuw" in _names(viewer_client)

    def test_the_viewer_finds_themselves(self, viewer_client):
        assert "Zeno Kijker" in _names(viewer_client)

    @pytest.mark.parametrize(("start_days", "end_days"), [(-90, -10), (10, 90)], ids=["ended", "planned"])
    def test_only_an_ended_or_planned_placement_counts_as_none(self, viewer_client, start_days, end_days):
        colleague = _account("Bob Tussendoor")
        _place(colleague, _assignment("Oude opdracht", start_days=start_days, end_days=end_days))

        card = next(card for card in _cards(viewer_client) if card["name"] == "Bob Tussendoor")
        assert card["no_assignment"] is True

    def test_a_placed_colleague_is_not_in_the_tail(self, viewer_client):
        _place(_account("Carla Geplaatst"), _assignment("Lopend"))

        cards = [card for card in _cards(viewer_client) if card["name"] == "Carla Geplaatst"]
        assert len(cards) == 1
        assert not cards[0].get("no_assignment")

    def test_a_colleague_without_account_stays_out(self, viewer_client):
        _without_account("Dirk Zonderaccount")
        assert "Dirk Zonderaccount" not in _names(viewer_client)

    def test_an_inactive_account_stays_out(self, viewer_client):
        colleague = _account("Eva Inactief")
        User.objects.filter(colleague=colleague).update(is_active=False)
        assert "Eva Inactief" not in _names(viewer_client)

    def test_a_placement_at_a_hidden_organization_hides_the_colleague_entirely(self, viewer_client):
        """A "Geen opdracht" card would give away a placement that has to stay hidden."""
        hidden = OrganizationUnit.objects.create(name="Algemene Inlichtingen- en Veiligheidsdienst")
        _place(_account("Frank Geheim"), _assignment("Geheim", org=hidden))
        assert "Frank Geheim" not in _names(viewer_client)

    def test_the_opdracht_view_has_no_tail(self, viewer_client):
        _account("Anna Nieuw")
        assert _cards(viewer_client, {"weergave": "opdracht"}) == []


@pytest.mark.django_db
class TestFilters:
    @pytest.fixture(autouse=True)
    def setup(self, viewer_client):
        self.client = viewer_client
        category = LabelCategory.objects.create(name="Expertise", color="#0066CC")
        self.python = Label.objects.create(name="Python", category=category)
        self.merk = Suborganization.objects.create(name="Merk A")
        self.anna = _account("Anna Nieuw", suborganization=self.merk)
        self.anna.labels.add(self.python)
        _account("Bob Nieuw")

    def _unplaced_names(self, params):
        return [card["name"] for card in _cards(self.client, params) if card.get("no_assignment")]

    def test_search_matches_the_name(self):
        assert self._unplaced_names({"zoek": "anna"}) == ["Anna Nieuw"]

    def test_label_filter_applies(self):
        assert self._unplaced_names({"labels": str(self.python.public_id)}) == ["Anna Nieuw"]

    def test_merk_filter_applies(self):
        assert self._unplaced_names({"merk": str(self.merk.public_id)}) == ["Anna Nieuw"]

    def test_unknown_label_matches_nothing(self):
        """Fail closed, like the placements: an unknown ?labels= is an empty list."""
        assert _cards(self.client, {"labels": "00000000-0000-0000-0000-000000000000"}) == []

    @pytest.mark.parametrize("value", ["foo", ""])
    def test_an_unknown_loopt_af_filters_nothing(self, value):
        """``_apply_filters`` ignores it, so the tail must stay too."""
        _place(_account("Carla Geplaatst"), _assignment("Lopend"))
        assert _names(self.client, {"loopt_af": value}) == _names(self.client)
        assert "Anna Nieuw" in _names(self.client, {"loopt_af": value})

    @pytest.mark.parametrize("param", ["rol", "org", "loopt_af"])
    def test_an_opdracht_filter_drops_the_tail(self, param):
        skill = Skill.objects.create(name="Ontwikkelaar")
        org = OrganizationUnit.objects.create(name="Ministerie", label="Min")
        _place(_account("Carla Geplaatst"), _assignment("Lopend", end_days=30, org=org), skill)
        value = {"rol": str(skill.public_id), "org": str(org.public_id), "loopt_af": "3m"}[param]

        names = _names(self.client, {param: value})
        assert names == ["Carla Geplaatst"]

    def test_an_opdracht_filter_drops_the_tail_from_the_persoon_count(self):
        skill = Skill.objects.create(name="Ontwikkelaar")
        _place(_account("Carla Geplaatst"), _assignment("Lopend"), skill)
        response = self.client.get(reverse("home"), {"rol": str(skill.public_id)})
        counts = {option["value"]: option["count"] for option in response.context_data["view_options"]}
        assert counts["persoon"] == 1


@pytest.mark.django_db
class TestOrderAndPagination:
    @pytest.fixture(autouse=True)
    def setup(self, viewer_client):
        self.client = viewer_client
        for name in ("Bob Geplaatst", "Dirk Geplaatst"):
            _place(_account(name), _assignment(f"Opdracht {name}"))
        for name in ("Carla Nieuw", "Anna Nieuw"):
            _account(name)

    def test_default_sort_puts_the_tail_last_by_name(self):
        names = _names(self.client)
        assert names[2:] == ["Anna Nieuw", "Carla Nieuw", "Zeno Kijker"]

    def test_name_sort_takes_the_tail_in_among_the_others(self):
        expected = ["Anna Nieuw", "Bob Geplaatst", "Carla Nieuw", "Dirk Geplaatst", "Zeno Kijker"]
        assert _names(self.client, {"order": "name"}) == expected
        assert _names(self.client, {"order": "-name"}) == expected[::-1]

    def test_assignment_sort_puts_the_tail_last(self):
        names = _names(self.client, {"order": "assignment"})
        assert names[2:] == ["Anna Nieuw", "Carla Nieuw", "Zeno Kijker"]

    def test_load_more_crosses_into_the_tail_without_gaps_or_doubles(self):
        """61 cards in all: the page boundary falls inside the tail."""
        for i in range(56):
            _account(f"Nieuw {i:03d}")

        seen = []
        for page in (1, 2):
            seen.extend(_names(self.client, {"pagina": str(page)}))

        expected_total = 2 + 2 + 56 + 1  # placed, unplaced, generated, viewer
        assert len(seen) == expected_total
        assert len(set(seen)) == expected_total

    @pytest.mark.parametrize("extra_placed", [56, 57], ids=["tail-starts-page-2", "tail-starts-on-the-last-card"])
    def test_load_more_at_the_boundary_between_placed_and_tail(self, extra_placed):
        """60 cards a page: the first unplaced card opens page 2, or closes page 1."""
        for i in range(extra_placed):
            _place(_account(f"Geplaatst {i:03d}"), _assignment(f"Opdracht {i:03d}"))

        first, second = (_cards(self.client, {"pagina": str(page)}) for page in (1, 2))
        placed_total = 2 + extra_placed
        assert [bool(card.get("no_assignment")) for card in first] == [False] * placed_total + [True] * (
            60 - placed_total
        )
        names = [card["name"] for card in first + second]
        assert len(names) == len(set(names)) == placed_total + 3  # Anna, Carla, viewer


@pytest.mark.django_db
class TestCard:
    def test_card_of_a_colleague_without_opdracht(self, viewer_client):
        colleague = _account("Anna Nieuw")
        card = next(card for card in _cards(viewer_client) if card["name"] == "Anna Nieuw")

        assert card["no_assignment"] is True
        assert card["assignment"] is None
        assert card["roles"] == []
        assert card["owned_count"] == 0
        assert card["summary"] == "Nu geen opdracht"
        assert f"collega={colleague.public_id}" in card["panel_url"]

    def test_business_manager_counts_current_and_planned_opdrachten_only(self, viewer_client):
        bm = _account("Bea Manager")
        _assignment("Lopend", owner=bm)
        _assignment("Gepland", start_days=10, end_days=90, owner=bm)
        _assignment("Afgelopen", start_days=-90, end_days=-10, owner=bm)

        card = next(card for card in _cards(viewer_client) if card["name"] == "Bea Manager")
        assert card["owned_count"] == 2
        assert card["roles"] == []

    def test_business_manager_count_leaves_out_hidden_organizations(self, viewer_client):
        bm = _account("Bea Manager")
        hidden = OrganizationUnit.objects.create(name="Algemene Inlichtingen- en Veiligheidsdienst")
        _assignment("Lopend", owner=bm)
        _assignment("Geheim", org=hidden, owner=bm)

        card = next(card for card in _cards(viewer_client) if card["name"] == "Bea Manager")
        assert card["owned_count"] == 1

    def test_business_manager_count_leaves_out_an_opdracht_with_a_hidden_and_a_visible_client(self, viewer_client):
        """The list drops the whole opdracht; the count must not keep it for its visible client."""
        bm = _account("Bea Manager")
        hidden = OrganizationUnit.objects.create(name="Algemene Inlichtingen- en Veiligheidsdienst")
        shared = _assignment("Gedeeld", org=hidden, owner=bm)
        AssignmentOrganizationUnit.objects.create(
            assignment=shared, organization=OrganizationUnit.objects.create(name="Ministerie"), role="INVOLVED"
        )

        card = next(card for card in _cards(viewer_client) if card["name"] == "Bea Manager")
        assert card["owned_count"] == 0

    def test_a_placed_business_manager_gets_the_placement_not_the_count(self, viewer_client):
        bm = _account("Bea Manager")
        _assignment("Eigen opdracht", owner=bm)
        _place(bm, _assignment("Plaatsing"))

        card = next(card for card in _cards(viewer_client) if card["name"] == "Bea Manager")
        assert not card.get("no_assignment")
        assert card["assignment"].name == "Plaatsing"

    def test_html_says_geen_opdracht(self, viewer_client):
        _account("Anna Nieuw")
        html = viewer_client.get(reverse("home")).content.decode()
        assert 'text="Nu geen opdracht"' in html

    def test_the_empty_second_row_is_hidden_from_assistive_tech(self, viewer_client):
        """The row only keeps the card at height; "Gegevens" should read as one item."""
        _account("Anna Nieuw")
        html = viewer_client.get(reverse("home")).content.decode()
        assert '<nldd-list-item size="sm" aria-hidden="true">' in html

    def test_html_names_the_business_manager_by_the_count_not_a_tag(self, viewer_client):
        """A tag on a card is a role on an opdracht; owning opdrachten is not one."""
        bm = _account("Bea Manager")
        _assignment("Lopend", owner=bm)
        html = viewer_client.get(reverse("home")).content.decode()
        assert 'text="Business Manager van 1 opdracht"' in html
        assert "<nldd-tag" not in html

    def test_an_ended_placement_stays_off_the_card(self, viewer_client):
        """History is for the colleague and business managers, in the panel (#410)."""
        colleague = _account("Bob Tussendoor")
        _place(colleague, _assignment("Geheime oude opdracht", start_days=-90, end_days=-10))

        html = viewer_client.get(reverse("home")).content.decode()
        assert "Bob Tussendoor" in html
        assert "Geheime oude opdracht" not in html

    def test_the_card_opens_the_colleague_panel(self, viewer_client):
        colleague = _account("Anna Nieuw")
        response = viewer_client.get(reverse("home"), {"collega": str(colleague.public_id)})
        assert response.context_data["panel_data"]["colleague"] == colleague
        assert response.context_data["panel_data"]["assignments"] == []


@pytest.mark.django_db
class TestImportNotice:
    """Not every opdracht is in Wies yet, so "Nu geen opdracht" is often not true;
    the page says why."""

    def test_the_page_says_not_every_opdracht_is_in_wies_yet(self, viewer_client):
        html = viewer_client.get(reverse("home")).content.decode()
        assert 'text="Nog niet alle opdrachten staan in Wies. We vullen de lijst aan."' in html
        assert 'data-dismiss-cookie="wies_missing_opdrachten_dismissed"' in html
        assert "<nldd-banner dismissible" in html
        # The close button says what it closes, not just "Verberg".
        assert '"components.banner.dismiss-action": "Melding verbergen"' in html

    def test_a_dismissed_banner_stays_away(self, viewer_client):
        viewer_client.cookies["wies_missing_opdrachten_dismissed"] = "1"
        html = viewer_client.get(reverse("home")).content.decode()
        assert "Nog niet alle opdrachten staan in Wies" not in html

    def test_a_filter_swap_does_not_repeat_the_banner(self, viewer_client):
        html = viewer_client.get(reverse("home"), headers={"HX-Request": "true"}).content.decode()
        assert "Nog niet alle opdrachten staan in Wies" not in html


@pytest.mark.django_db
class TestCounts:
    @pytest.fixture(autouse=True)
    def setup(self, viewer_client):
        self.client = viewer_client
        self.category = LabelCategory.objects.create(name="Expertise", color="#0066CC")
        self.python = Label.objects.create(name="Python", category=self.category)
        self.merk = Suborganization.objects.create(name="Merk A")
        placed = _account("Carla Geplaatst", suborganization=self.merk)
        placed.labels.add(self.python)
        _place(placed, _assignment("Lopend"))
        unplaced = _account("Anna Nieuw", suborganization=self.merk)
        unplaced.labels.add(self.python)

    def _view_counts(self, params=None):
        response = self.client.get(reverse("home"), params or {})
        return {option["value"]: option["count"] for option in response.context_data["view_options"]}

    def _option_count(self, params, group_name, value):
        response = self.client.get(reverse("home"), params or {})
        group = next(g for g in response.context_data["filter_groups"] if g["name"] == group_name)
        return next(o["count"] for o in group["options"] if o["value"] == value)

    def test_persoon_count_includes_the_tail_in_both_views(self):
        # Carla, Anna and the viewer.
        assert self._view_counts() == {"persoon": 3, "opdracht": 1}
        assert self._view_counts({"weergave": "opdracht"}) == {"persoon": 3, "opdracht": 1}

    def test_label_and_merk_counts_include_the_tail(self):
        assert self._option_count({}, "labels", str(self.python.public_id)) == 2
        assert self._option_count({}, "merk", str(self.merk.public_id)) == 2

    def test_label_count_matches_the_cards_it_yields(self):
        count = self._option_count({}, "labels", str(self.python.public_id))
        assert len(_cards(self.client, {"labels": str(self.python.public_id)})) == count

    def test_opdracht_view_label_count_leaves_the_tail_out(self):
        assert self._option_count({"weergave": "opdracht"}, "labels", str(self.python.public_id)) == 1


def _grant_user_admin(user):
    group, _created = Group.objects.get_or_create(name=ROLE_USER_ADMIN)
    user.groups.add(group)


ROLE_SETUPS = {
    "consultant": (grant_consultant, "consultant@rijksoverheid.nl"),
    "business_manager": (grant_business_manager, "bm@rijksoverheid.nl"),
    "user_admin": (_grant_user_admin, "beheer@rijksoverheid.nl"),
    "staff": (lambda user: user, STAFF_EMAIL),
}


@pytest.mark.django_db
class TestPerRole:
    """Every role sees the card; only the colleague and a business manager see the history behind it."""

    @pytest.fixture(autouse=True)
    def setup(self, settings):
        settings.STAFF_EMAILS = [STAFF_EMAIL]
        self.colleague = _account("Bob Tussendoor")
        _place(self.colleague, _assignment("Oude opdracht", start_days=-90, end_days=-10))

    def _client_for(self, role):
        grant, email = ROLE_SETUPS[role]
        user = User.objects.create_user(email=email, first_name="Kijker", last_name=role)
        grant(user)
        client = Client()
        client.force_login(user)
        return client

    def _panel_names(self, client, colleague):
        response = client.get(reverse("home"), {"collega": str(colleague.public_id)})
        return [entry["name"] for entry in response.context_data["panel_data"]["assignments"]]

    @pytest.mark.parametrize("role", list(ROLE_SETUPS))
    def test_every_role_sees_the_card(self, role):
        assert "Bob Tussendoor" in _names(self._client_for(role))

    @pytest.mark.parametrize("role", list(ROLE_SETUPS))
    def test_every_role_sees_their_own_card(self, role):
        client = self._client_for(role)
        assert f"Kijker {role}" in _names(client)

    @pytest.mark.parametrize(
        ("role", "sees_history"),
        [
            ("consultant", False),
            ("business_manager", True),
            ("user_admin", False),
            ("staff", False),
        ],
    )
    def test_history_in_the_panel_only_for_a_business_manager(self, role, sees_history):
        names = self._panel_names(self._client_for(role), self.colleague)
        assert ("Oude opdracht" in names) is sees_history

    def test_the_colleague_sees_their_own_history(self):
        client = Client()
        client.force_login(self.colleague.user)
        assert "Oude opdracht" in self._panel_names(client, self.colleague)
