"""Tests for the ContractPeriod inline formset in the edit-user modal.

Exploratory BM-feature (branch ``explore-bm-views``). These guard against the
formset rows collapsing into one another — each period's date fields must be
independent both in the rendered HTML (distinct ids/names) and on save.
"""

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.editables.assignment import _services_initial
from wies.core.models import Assignment, Colleague, ContractPeriod, Placement, Service
from wies.core.services.assignments import apply_services_to_assignment

User = get_user_model()


class ContractPeriodFormsetTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(email="admin@rijksoverheid.nl", first_name="Admin", last_name="User")
        self.admin.user_permissions.add(Permission.objects.get(codename="change_user"))

        self.edited = User.objects.create_user(email="collega@rijksoverheid.nl", first_name="Cor", last_name="Lega")
        self.colleague = Colleague.objects.create(
            user=self.edited, name="Cor Lega", email=self.edited.email, source="wies"
        )
        self.p1 = ContractPeriod.objects.create(
            colleague=self.colleague, hours_per_week=40, start_date="2020-01-01", end_date="2021-12-31"
        )
        self.p2 = ContractPeriod.objects.create(
            colleague=self.colleague, hours_per_week=36, start_date="2022-01-01", end_date=None
        )
        self.client.force_login(self.admin)
        self.url = reverse("user-edit", args=[self.edited.pk])

    def test_rows_render_with_distinct_ids_and_values(self):
        """Each period's date inputs must carry a unique id and its own value."""
        html = self.client.get(self.url).content.decode()

        # Collect the id of every start_date input across rows.
        start_ids = re.findall(
            r'name="contract_periods-\d+-start_date"[^>]*?id\s*=\s*"([^"]+)"',
            html,
            re.S,
        )
        # Fallback: id may appear before name depending on attr order.
        if not start_ids:
            start_ids = re.findall(r'id\s*=\s*"(id_contract_periods-\d+-start_date)"', html)

        assert len(start_ids) >= 2, f"expected >=2 start_date inputs, got {start_ids}"
        assert len(start_ids) == len(set(start_ids)), f"duplicate ids: {start_ids}"

        # The two existing rows keep their own distinct values.
        assert "2020-01-01" in html
        assert "2022-01-01" in html

    def test_editing_one_row_leaves_others_untouched(self):
        """Changing row 0's start_date must not alter row 1 or fabricate dates."""
        data = {
            "first_name": "Cor",
            "last_name": "Lega",
            "email": self.edited.email,
            "contract_periods-TOTAL_FORMS": "3",
            "contract_periods-INITIAL_FORMS": "2",
            "contract_periods-MIN_NUM_FORMS": "0",
            "contract_periods-MAX_NUM_FORMS": "1000",
            "contract_periods-0-id": str(self.p1.id),
            "contract_periods-0-hours_per_week": "40",
            "contract_periods-0-start_date": "2020-06-06",
            "contract_periods-0-end_date": "2021-12-31",
            "contract_periods-1-id": str(self.p2.id),
            "contract_periods-1-hours_per_week": "36",
            "contract_periods-1-start_date": "2022-01-01",
            "contract_periods-1-end_date": "",
            "contract_periods-2-id": "",
            "contract_periods-2-hours_per_week": "",
            "contract_periods-2-start_date": "",
            "contract_periods-2-end_date": "",
        }
        resp = self.client.post(self.url, data)
        assert resp.status_code in (200, 302), resp.status_code

        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        assert str(self.p1.start_date) == "2020-06-06"
        assert str(self.p1.end_date) == "2021-12-31"
        # Row 1 is completely unchanged.
        assert str(self.p2.start_date) == "2022-01-01"
        assert self.p2.end_date is None


class TeamEditorHoursTest(TestCase):
    """Uren per week is editable per placement through the Team editor."""

    def setUp(self):
        self.colleague = Colleague.objects.create(name="Plaats Baar", email="pb@rijksoverheid.nl", source="wies")
        self.assignment = Assignment.objects.create(name="Opdracht", source="wies")
        self.service = Service.objects.create(assignment=self.assignment, description="rol", source="wies")
        self.placement = Placement.objects.create(
            colleague=self.colleague, service=self.service, source="wies", assignment_hours_per_week=24
        )

    def _rows_to_services_data(self, rows, override):
        return [
            {
                "id": r["id"],
                "placement_id": r["placement_id"],
                "description": r["description"],
                "skill_id": int(r["skill"]) if r["skill"] else None,
                "new_skill_name": None,
                "status": "OPEN",
                "colleague_id": r["colleague"].id if r["colleague"] else None,
                "has_custom_period": r["has_custom_period"],
                "placement_start_date": r["placement_start_date"] if r["has_custom_period"] else None,
                "placement_end_date": r["placement_end_date"] if r["has_custom_period"] else None,
                "assignment_hours_per_week": override.get(r["placement_id"], r["assignment_hours_per_week"]),
            }
            for r in rows
        ]

    def test_initial_seeds_current_hours(self):
        row = _services_initial(self.assignment)[0]
        assert row["assignment_hours_per_week"] == 24

    def test_editing_hours_persists_on_placement(self):
        rows = _services_initial(self.assignment)
        data = self._rows_to_services_data(rows, override={self.placement.id: 28})
        apply_services_to_assignment(self.assignment, data)
        self.placement.refresh_from_db()
        assert self.placement.assignment_hours_per_week == 28

    def test_clearing_hours_sets_none(self):
        rows = _services_initial(self.assignment)
        data = self._rows_to_services_data(rows, override={self.placement.id: None})
        apply_services_to_assignment(self.assignment, data)
        self.placement.refresh_from_db()
        assert self.placement.assignment_hours_per_week is None
