"""Contract hours per colleague and hours per week per role, and what Bezetting
makes of them."""

import re
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from wies.core.models import Assignment, Colleague, ContractPeriod, Placement, Service, Skill
from wies.core.roles import setup_roles
from wies.core.services.occupancy import BUCKET_FULL, BUCKET_PARTIAL, colleague_occupancy, occupancy_summary

User = get_user_model()


def _consultant(name, email):
    user = User.objects.create(email=email, onboarding_completed_at=timezone.now())
    user.groups.add(Group.objects.get(name="Consultant"))
    return Colleague.objects.create(name=name, email=email, source="wies", user=user)


def _placement(colleague, name, start, end, hours=None):
    assignment = Assignment.objects.create(name=name, source="wies")
    service = Service.objects.create(assignment=assignment, description=name, source="wies", hours_per_week=hours)
    return Placement.objects.create(
        colleague=colleague,
        service=service,
        period_source="PLACEMENT",
        specific_start_date=start,
        specific_end_date=end,
        source="wies",
    )


class ContractPeriodModelTest(TestCase):
    def setUp(self):
        self.colleague = Colleague.objects.create(name="Cora Contract", email="cora@x.nl", source="wies")
        self.today = timezone.now().date()

    def test_end_before_start_is_rejected(self):
        period = ContractPeriod(
            colleague=self.colleague, hours_per_week=36, start_date=self.today, end_date=self.today - timedelta(days=1)
        )
        with pytest.raises(ValidationError) as ctx:
            period.full_clean()
        assert "end_date" in ctx.value.message_dict

    def test_hours_outside_range_are_rejected(self):
        for hours in (0, 41):
            period = ContractPeriod(colleague=self.colleague, hours_per_week=hours, start_date=self.today)
            with pytest.raises(ValidationError) as ctx:
                period.full_clean()
            assert "hours_per_week" in ctx.value.message_dict

    def test_overlapping_periods_are_rejected(self):
        ContractPeriod.objects.create(
            colleague=self.colleague, hours_per_week=32, start_date=self.today - timedelta(days=100)
        )
        overlapping = ContractPeriod(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        with pytest.raises(ValidationError) as ctx:
            overlapping.full_clean()
        assert "start_date" in ctx.value.message_dict

    def test_consecutive_periods_are_allowed(self):
        ContractPeriod.objects.create(
            colleague=self.colleague,
            hours_per_week=32,
            start_date=self.today - timedelta(days=100),
            end_date=self.today - timedelta(days=1),
        )
        ContractPeriod(colleague=self.colleague, hours_per_week=36, start_date=self.today).full_clean()

    def test_editing_a_period_does_not_overlap_with_itself(self):
        period = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=32, start_date=self.today)
        period.hours_per_week = 36
        period.full_clean()


class OccupancyHoursTest(TestCase):
    def setUp(self):
        setup_roles()
        self.today = timezone.now().date()
        self.start = self.today - timedelta(days=10)
        self.end = self.today + timedelta(days=200)

    def test_roles_that_do_not_fill_the_contract_make_a_partial_row(self):
        colleague = _consultant("Piet Partial", "piet@x.nl")
        ContractPeriod.objects.create(colleague=colleague, hours_per_week=36, start_date=self.start)
        _placement(colleague, "Kleine klus", self.start, self.end, hours=16)
        _placement(colleague, "Andere klus", self.start, self.end, hours=8)

        [row] = colleague_occupancy(self.today)

        assert row.bucket == BUCKET_PARTIAL
        assert (row.contract_hours, row.active_hours, row.unfilled_hours) == (36, 24, 12)
        assert occupancy_summary([row])["partial_count"] == 1

    def test_roles_that_fill_the_contract_make_a_full_row(self):
        colleague = _consultant("Fenna Full", "fenna@x.nl")
        ContractPeriod.objects.create(colleague=colleague, hours_per_week=32, start_date=self.start)
        _placement(colleague, "Voltijd", self.start, self.end, hours=32)

        [row] = colleague_occupancy(self.today)

        assert row.bucket == BUCKET_FULL
        assert row.unfilled_hours == 0

    def test_a_role_without_hours_keeps_the_row_full(self):
        colleague = _consultant("Onno Onbekend", "onno@x.nl")
        ContractPeriod.objects.create(colleague=colleague, hours_per_week=36, start_date=self.start)
        _placement(colleague, "Met uren", self.start, self.end, hours=8)
        _placement(colleague, "Zonder uren", self.start, self.end)

        [row] = colleague_occupancy(self.today)

        assert row.bucket == BUCKET_FULL
        assert row.active_hours is None
        assert row.unfilled_hours is None

    def test_without_contract_hours_a_placed_colleague_is_full(self):
        colleague = _consultant("Geen Contract", "geen@x.nl")
        _placement(colleague, "Klus", self.start, self.end, hours=8)

        [row] = colleague_occupancy(self.today)

        assert row.bucket == BUCKET_FULL
        assert row.contract_hours is None

    def test_bench_row_carries_the_whole_contract_as_free(self):
        colleague = _consultant("Bea Bank", "bea@x.nl")
        ContractPeriod.objects.create(colleague=colleague, hours_per_week=24, start_date=self.start)

        [row] = colleague_occupancy(self.today)

        assert row.bucket == "bench"
        assert row.unfilled_hours == 24

    def test_contract_hours_follow_the_period_covering_today(self):
        colleague = _consultant("Wisse Wissel", "wisse@x.nl")
        ContractPeriod.objects.create(
            colleague=colleague,
            hours_per_week=40,
            start_date=self.today - timedelta(days=400),
            end_date=self.today - timedelta(days=1),
        )
        ContractPeriod.objects.create(colleague=colleague, hours_per_week=32, start_date=self.today)

        [row] = colleague_occupancy(self.today)

        assert row.contract_hours == 32

    def test_partial_rows_sort_between_bench_and_full_by_free_hours(self):
        little = _consultant("Little Free", "little@x.nl")
        ContractPeriod.objects.create(colleague=little, hours_per_week=36, start_date=self.start)
        _placement(little, "Bijna vol", self.start, self.end, hours=32)
        much = _consultant("Much Free", "much@x.nl")
        ContractPeriod.objects.create(colleague=much, hours_per_week=36, start_date=self.start)
        _placement(much, "Half", self.start, self.end, hours=16)
        full = _consultant("Full Stop", "full@x.nl")
        ContractPeriod.objects.create(colleague=full, hours_per_week=36, start_date=self.start)
        _placement(full, "Vol", self.start, self.end, hours=36)
        _consultant("Bank Zit", "bank@x.nl")

        names = [r.colleague.name for r in colleague_occupancy(self.today)]

        assert names == ["Bank Zit", "Much Free", "Little Free", "Full Stop"]

    def test_segments_carry_the_role_hours(self):
        colleague = _consultant("Seg Ment", "seg@x.nl")
        _placement(colleague, "Klus", self.start, self.end, hours=24)

        [row] = colleague_occupancy(self.today)

        assert row.segments[0].hours_per_week == 24


class BezettingPartialStatusViewTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()
        self.url = reverse("bezetting")
        bdm = User.objects.create(email="bdm@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        bdm.groups.add(Group.objects.get(name="Business Development Manager"))
        self.client.force_login(bdm)
        today = timezone.now().date()
        start, end = today - timedelta(days=10), today + timedelta(days=200)
        self.partial = _consultant("Piet Partial", "piet@x.nl")
        ContractPeriod.objects.create(colleague=self.partial, hours_per_week=36, start_date=start)
        _placement(self.partial, "Kleine klus", start, end, hours=16)
        self.full = _consultant("Fenna Full", "fenna@x.nl")
        ContractPeriod.objects.create(colleague=self.full, hours_per_week=36, start_date=start)
        _placement(self.full, "Voltijd", start, end, hours=36)

    def test_partial_card_counts_and_row_shows_free_hours(self):
        body = self.client.get(self.url).content.decode()
        assert 'data-status="partial"' in body
        assert "20 uur vrij" in body
        assert "uur ingezet" not in body

    def test_partial_status_filters_to_partial_rows(self):
        body = self.client.get(self.url, {"status": "partial"}).content.decode()
        assert "Piet Partial" in body
        assert "Fenna Full" not in body


class ProfileContractPeriodTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()
        self.today = timezone.now().date()
        self.user = User.objects.create(email="me@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        self.colleague = Colleague.objects.create(
            name="Ik Zelf", email="me@rijksoverheid.nl", source="wies", user=self.user
        )
        self.client.force_login(self.user)

    def test_profile_lists_periods_and_offers_to_add(self):
        ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        body = self.client.get(reverse("user-profile")).content.decode()
        assert "36 uur" in body
        assert "Contractperiode toevoegen" in body

    def test_add_sheet_saves_a_period(self):
        response = self.client.post(
            reverse("profile-contract-period-add"),
            {"hours_per_week": "32", "start_date": self.today.isoformat(), "end_date": ""},
        )
        assert response.status_code == 200
        # The sheet closes through its emptied mount; the block comes back refreshed.
        body = response.content.decode()
        assert 'id="contractPeriodMount" hx-swap-oob="innerHTML"' in body
        assert re.search(r'id="contractPeriodsBlock"\s+hx-swap-oob="outerHTML"', body)
        assert "32 uur" in body
        [period] = ContractPeriod.objects.filter(colleague=self.colleague)
        assert (period.hours_per_week, period.start_date, period.end_date) == (32, self.today, None)

    def test_overlap_comes_back_as_a_field_error(self):
        ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        response = self.client.post(
            reverse("profile-contract-period-add"),
            {"hours_per_week": "32", "start_date": self.today.isoformat(), "end_date": ""},
        )
        assert response.status_code == 200
        assert "overlapt" in response.content.decode()
        assert ContractPeriod.objects.count() == 1

    def test_edit_and_delete_own_period(self):
        period = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        self.client.post(
            reverse("profile-contract-period-edit", args=[period.public_id]),
            {"hours_per_week": "24", "start_date": self.today.isoformat(), "end_date": ""},
        )
        period.refresh_from_db()
        assert period.hours_per_week == 24
        response = self.client.post(reverse("profile-contract-period-delete", args=[period.public_id]))
        assert response.status_code == 200
        assert "Nog niet ingevuld" in response.content.decode()
        assert not ContractPeriod.objects.filter(pk=period.pk).exists()

    def test_someone_elses_period_is_not_found(self):
        other = Colleague.objects.create(name="Ander", email="ander@x.nl", source="wies")
        period = ContractPeriod.objects.create(colleague=other, hours_per_week=36, start_date=self.today)
        assert self.client.get(reverse("profile-contract-period-edit", args=[period.public_id])).status_code == 404
        assert self.client.post(reverse("profile-contract-period-delete", args=[period.public_id])).status_code == 404
        assert ContractPeriod.objects.filter(pk=period.pk).exists()

    def test_colleague_panel_shows_current_contract_hours(self):
        ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        body = self.client.get(reverse("home"), {"collega": self.colleague.public_id}).content.decode()
        assert "36 uur" in body


class ServiceHoursTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()
        self.bdm = User.objects.create(email="bdm@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        self.bdm.groups.add(Group.objects.get(name="Business Development Manager"))
        self.owner = Colleague.objects.create(
            name="Bas BDM", email="bdm@rijksoverheid.nl", source="wies", user=self.bdm
        )
        self.client.force_login(self.bdm)
        self.assignment = Assignment.objects.create(name="Urenopdracht", source="wies", owner=self.owner)
        self.skill = Skill.objects.create(name="Data engineer")

    def test_member_form_saves_hours_on_the_role(self):
        response = self.client.post(
            reverse("assignment-member-edit", args=[self.assignment.public_id]),
            {
                "skill": str(self.skill.public_id),
                "description": "",
                "hours_per_week": "24",
                "is_filled": "aanvraag",
                "has_custom_period": "on",
            },
        )
        assert response.status_code == 204, response.content
        [service] = self.assignment.services.all()
        assert service.hours_per_week == 24

    def test_team_row_and_card_show_the_hours(self):
        Service.objects.create(
            assignment=self.assignment, description="", skill=self.skill, source="wies", hours_per_week=24
        )
        panel = self.client.get(
            f"/opdrachten/?opdracht={self.assignment.public_id}",
            headers={"hx-request": "true", "hx-target": "side-panel-content"},
        ).content.decode()
        assert "24 uur" in panel
        cards = self.client.get(reverse("assignment-list")).content.decode()
        assert "Data engineer · 24 u" in cards

    def test_hours_above_the_maximum_are_rejected(self):
        response = self.client.post(
            reverse("assignment-member-edit", args=[self.assignment.public_id]),
            {
                "skill": str(self.skill.public_id),
                "hours_per_week": "41",
                "is_filled": "aanvraag",
                "has_custom_period": "on",
            },
        )
        assert response.status_code == 200
        assert self.assignment.services.count() == 0


class GeneratorHoursTest(TestCase):
    def test_base_profile_seeds_contract_periods_and_role_hours(self):
        call_command("load_dummy_data", "--profile", "base", verbosity=0)
        assert ContractPeriod.objects.filter(end_date__isnull=True).count() == Colleague.objects.count()
        assert Service.objects.filter(hours_per_week__isnull=False).exists()
        assert Service.objects.filter(hours_per_week__isnull=True).exists()


class UserSheetContractPeriodTest(TestCase):
    """A beheerder keeps contract periods on the user sheet (beheer/gebruikers)."""

    def setUp(self):
        setup_roles()
        self.client = Client()
        self.today = timezone.now().date()
        self.admin = User.objects.create(email="admin@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        self.admin.groups.add(Group.objects.get(name="Beheerder"))
        self.client.force_login(self.admin)
        self.user = User.objects.create(
            email="kees@rijksoverheid.nl", first_name="Kees", last_name="Bos", onboarding_completed_at=timezone.now()
        )
        self.colleague = Colleague.objects.create(
            name="Kees Bos", email="kees@rijksoverheid.nl", source="wies", user=self.user
        )
        self.add_url = reverse("user-contract-period-add", args=[self.user.public_id])

    def test_sheet_lists_periods_with_the_admin_actions(self):
        period = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        body = self.client.get(reverse("user-edit", args=[self.user.public_id])).content.decode()
        assert "Contracturen" in body
        assert "36 uur" in body
        assert self.add_url in body
        assert reverse("user-contract-period-edit", args=[period.public_id]) in body
        assert reverse("user-contract-period-delete", args=[period.public_id]) in body
        assert 'name="contract-TOTAL_FORMS"' not in body

    def test_admin_adds_a_period_and_gets_the_block_back(self):
        response = self.client.post(
            self.add_url, {"hours_per_week": "36", "start_date": self.today.isoformat(), "end_date": ""}
        )
        assert response.status_code == 200, response.content
        body = response.content.decode()
        assert 'id="contractPeriodMount" hx-swap-oob="innerHTML"' in body
        assert "36 uur" in body
        [period] = self.colleague.contract_periods.all()
        assert (period.hours_per_week, period.start_date) == (36, self.today)

    def test_admin_edits_and_deletes_a_period(self):
        period = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        self.client.post(
            reverse("user-contract-period-edit", args=[period.public_id]),
            {"hours_per_week": "24", "start_date": self.today.isoformat(), "end_date": ""},
        )
        period.refresh_from_db()
        assert period.hours_per_week == 24
        response = self.client.post(reverse("user-contract-period-delete", args=[period.public_id]))
        assert response.status_code == 200
        assert "Nog niet ingevuld" in response.content.decode()
        assert not ContractPeriod.objects.filter(pk=period.pk).exists()

    def test_overlap_keeps_the_sheet_open_with_the_error(self):
        ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        response = self.client.post(
            self.add_url, {"hours_per_week": "32", "start_date": self.today.isoformat(), "end_date": ""}
        )
        assert response.status_code == 200
        body = response.content.decode()
        assert "overlapt" in body
        assert "contractPeriodMount" not in body
        assert ContractPeriod.objects.count() == 1

    def test_user_without_colleague_gets_no_block_and_no_add(self):
        loose = User.objects.create(email="los@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        body = self.client.get(reverse("user-edit", args=[loose.public_id])).content.decode()
        assert "Contracturen" not in body
        assert self.client.get(reverse("user-contract-period-add", args=[loose.public_id])).status_code == 404

    def test_consultant_may_not_touch_someone_elses_periods(self):
        period = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        consultant = User.objects.create(email="c@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        consultant.groups.add(Group.objects.get(name="Consultant"))
        self.client.force_login(consultant)
        assert self.client.get(self.add_url).status_code == 403
        assert self.client.get(reverse("user-contract-period-edit", args=[period.public_id])).status_code == 403
        assert self.client.post(reverse("user-contract-period-delete", args=[period.public_id])).status_code == 403
        assert ContractPeriod.objects.filter(pk=period.pk).exists()
