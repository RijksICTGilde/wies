"""The sort dropdown on "Wie zit waar?" (home) updates the list in place.

Sorting used to reload the whole page. It now does an htmx-swap of ``#results``
plus out-of-band swaps of the list (``#placement-list``) and the sort control
(``#sort-control``). The sort control must travel OOB because the toolbar itself
is only rendered on full page loads; without it the button label and the ticked
radio would keep showing the previous order after a swap.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import (
    Assignment,
    Colleague,
    Placement,
    Service,
    Skill,
)

User = get_user_model()


class SortSwapTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="viewer@rijksoverheid.nl", first_name="V", last_name="iewer")
        self.skill = Skill.objects.create(name="Python Developer")

        # Two assignments whose names sort in a known order, so ?order=assignment
        # (A-Z) and ?order=-assignment (Z-A) produce opposite row orders.
        self.p_alpha = self._create_placement("Alice", "Alpha opdracht")
        self.p_zulu = self._create_placement("Bob", "Zulu opdracht")

        self.url = reverse("home")

    def _create_placement(self, colleague_name, assignment_name):
        colleague = Colleague.objects.create(
            name=colleague_name,
            email=f"{colleague_name.lower()}@rijksoverheid.nl",
            source="wies",
        )
        assignment = Assignment.objects.create(
            name=assignment_name,
            source="wies",
            start_date=date(2025, 1, 1),
            end_date=date(2030, 1, 1),
        )
        service = Service.objects.create(assignment=assignment, description="Service", skill=self.skill, source="wies")
        return Placement.objects.create(colleague=colleague, service=service, period_source="ASSIGNMENT", source="wies")

    def test_htmx_sort_returns_container_with_oob_list_and_sort_control(self):
        """An htmx sort request returns the results line (swap target) plus the
        list and the sort control as out-of-band swaps."""
        self.client.force_login(self.user)

        response = self.client.get(self.url, {"order": "-assignment"}, headers={"hx-request": "true"})

        assert response.status_code == 200
        content = response.content.decode()
        assert 'id="results"' in content
        assert 'id="placement-list"' in content
        assert 'id="sort-control"' in content
        # Both the list and the sort control ride along OOB in the same response.
        assert 'hx-swap-oob="outerHTML"' in content

    def test_htmx_sort_control_reflects_chosen_order(self):
        """After a swap the OOB sort control shows the chosen order as its label
        and marks that radio selected, so the button is not left stale."""
        self.client.force_login(self.user)

        response = self.client.get(self.url, {"order": "-assignment"}, headers={"hx-request": "true"})
        content = response.content.decode()

        # The button reflects the current choice (Z-A), not the default label.
        assert "Opdracht (Z-A)" in content

    def test_order_actually_sorts_rows(self):
        """?order= reorders the rendered rows (guards the swap is meaningful)."""
        self.client.force_login(self.user)

        asc = self.client.get(self.url, {"order": "assignment"}).content.decode()
        desc = self.client.get(self.url, {"order": "-assignment"}).content.decode()

        assert asc.index("Alpha opdracht") < asc.index("Zulu opdracht")
        assert desc.index("Zulu opdracht") < desc.index("Alpha opdracht")

    def test_full_page_load_renders_toolbar_sort_control(self):
        """On a normal (non-htmx) load the sort control renders inside the
        toolbar without an OOB attribute."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)
        content = response.content.decode()

        assert 'id="sort-control"' in content
        # The full-page render of the control is not an OOB fragment; it carries
        # no hx-swap-oob on the sort-control element itself.
        sort_control_tag = content[content.index('id="sort-control"') - 40 : content.index('id="sort-control"') + 60]
        assert "hx-swap-oob" not in sort_control_tag
