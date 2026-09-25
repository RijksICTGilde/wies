"""Contract hours per colleague and hours per week per role, and what Bezetting
makes of them."""

import re
import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from wies.core.editables.service import ServiceEditables
from wies.core.models import Assignment, Colleague, ContractPeriod, Event, Placement, Service, Skill
from wies.core.permission_engine import Verb, has_permission
from wies.core.roles import (
    ROLE_BDM,
    ROLE_CONSULTANT,
    ROLE_OFFICE_ASSISTANT,
    can_view_role_hours,
    setup_roles,
)
from wies.core.services.occupancy import BUCKET_FULL, BUCKET_PARTIAL, colleague_occupancy, occupancy_summary
from wies.core.services.placements import placement_edit_specs

from .role_helpers import STAFF_EMAIL, make_staff_user

User = get_user_model()


def _consultant(name, email):
    user = User.objects.create(email=email, onboarding_completed_at=timezone.now())
    user.groups.add(Group.objects.get(name=ROLE_CONSULTANT))
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

    def test_a_period_ending_on_the_day_the_next_starts_is_rejected(self):
        # Both cover that day; the old one has to end the day before.
        ContractPeriod.objects.create(
            colleague=self.colleague,
            hours_per_week=32,
            start_date=self.today - timedelta(days=100),
            end_date=self.today,
        )
        with pytest.raises(ValidationError):
            ContractPeriod(colleague=self.colleague, hours_per_week=36, start_date=self.today).full_clean()

    def test_a_second_open_ended_period_is_rejected(self):
        ContractPeriod.objects.create(
            colleague=self.colleague, hours_per_week=32, start_date=self.today - timedelta(days=100)
        )
        with pytest.raises(ValidationError):
            ContractPeriod(
                colleague=self.colleague, hours_per_week=36, start_date=self.today + timedelta(days=30)
            ).full_clean()

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
        bdm.groups.add(Group.objects.get(name=ROLE_BDM))
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
        card = re.search(r'data-status="partial".*?</button>', body, re.DOTALL).group(0)
        assert re.search(r"<span class=\"bezetting-stat__count\">1</span>", card)
        assert "20 uur vrij" in body
        # Someone exactly full shows no hours at all on the second line.
        fenna = body.split("Fenna Full")[1].split("</nldd-identity>")[0]
        assert "uur" not in fenna

    def test_a_role_ending_today_still_counts_and_ended_yesterday_does_not(self):
        today = timezone.now().date()
        start = today - timedelta(days=100)
        ending = _consultant("Els Eindigt", "els@x.nl")
        ContractPeriod.objects.create(colleague=ending, hours_per_week=36, start_date=start)
        _placement(ending, "Tot vandaag", start, today, hours=36)
        ended = _consultant("Gerda Gisteren", "gerda@x.nl")
        ContractPeriod.objects.create(colleague=ended, hours_per_week=36, start_date=start)
        _placement(ended, "Tot gisteren", start, today - timedelta(days=1), hours=36)
        rows = {r.colleague.id: r for r in colleague_occupancy(today)}
        assert (rows[ending.id].bucket, rows[ending.id].unfilled_hours) == (BUCKET_FULL, 0)
        assert (rows[ended.id].bucket, rows[ended.id].unfilled_hours) == ("bench", 36)

    def test_a_contract_ending_today_still_counts(self):
        today = timezone.now().date()
        last_day = _consultant("Loes Laatste", "loes@x.nl")
        ContractPeriod.objects.create(
            colleague=last_day, hours_per_week=32, start_date=today - timedelta(days=100), end_date=today
        )
        row = next(r for r in colleague_occupancy(today) if r.colleague.id == last_day.id)
        assert row.contract_hours == 32

    def test_more_role_hours_than_contract_shows_as_over_contract(self):
        today = timezone.now().date()
        over = _consultant("Olga Over", "olga@x.nl")
        start, end = today - timedelta(days=10), today + timedelta(days=200)
        ContractPeriod.objects.create(colleague=over, hours_per_week=24, start_date=start)
        _placement(over, "Grote klus", start, end, hours=36)
        row = next(r for r in colleague_occupancy(today) if r.colleague.id == over.id)
        assert (row.bucket, row.unfilled_hours) == (BUCKET_FULL, -12)
        body = self.client.get(self.url).content.decode()
        assert "12 uur boven contract" in body

    def test_a_contract_that_starts_later_or_has_ended_says_so(self):
        today = timezone.now().date()
        later = _consultant("Lara Later", "lara@x.nl")
        ContractPeriod.objects.create(colleague=later, hours_per_week=32, start_date=today + timedelta(days=20))
        gone = _consultant("Gijs Gone", "gijs@x.nl")
        ContractPeriod.objects.create(
            colleague=gone,
            hours_per_week=36,
            start_date=today - timedelta(days=400),
            end_date=today - timedelta(days=1),
        )
        body = self.client.get(self.url).content.decode()
        assert f"32 uur vanaf {date_format(today + timedelta(days=20), 'j b Y')}" in body
        assert "geen lopend contract" in body
        assert "contracturen onbekend" not in body.split("Gijs Gone")[1].split("</nldd-identity>")[0]

    def test_partial_status_filters_to_partial_rows(self):
        body = self.client.get(self.url, {"status": "partial"}).content.decode()
        assert "Piet Partial" in body
        assert "Fenna Full" not in body


class ProfileContractPeriodTest(TestCase):
    """Contract hours are not on the profile, for no role: they are a matter for
    the colleague and their manager, and Wies shows them where they are kept."""

    def setUp(self):
        setup_roles()
        self.client = Client()
        self.today = timezone.now().date()
        self.user = User.objects.create(email="me@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        self.user.groups.add(Group.objects.get(name=ROLE_CONSULTANT))
        self.colleague = Colleague.objects.create(
            name="Ik Zelf", email="me@rijksoverheid.nl", source="wies", user=self.user
        )
        self.client.force_login(self.user)
        self.add_url = reverse("contract-period-add", args=[self.colleague.public_id])

    def test_profile_shows_no_contract_hours_to_any_role(self):
        ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        for group in (None, ROLE_BDM, ROLE_OFFICE_ASSISTANT):
            if group:
                self.user.groups.add(Group.objects.get(name=group))
            body = self.client.get(reverse("user-profile")).content.decode()
            assert "Contracturen" not in body, group
            assert "36 uur" not in body, group

    def test_consultant_may_not_keep_periods(self):
        period = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        assert self.client.get(self.add_url).status_code == 403
        assert (
            self.client.post(self.add_url, {"hours_per_week": "32", "start_date": self.today.isoformat()}).status_code
            == 403
        )
        assert self.client.get(reverse("contract-period-edit", args=[period.public_id])).status_code == 403
        assert self.client.post(reverse("contract-period-delete", args=[period.public_id])).status_code == 403
        assert ContractPeriod.objects.count() == 1

    def test_colleague_panel_keeps_contract_hours_from_consultants(self):
        """Contract hours are for who plans with them; the hours of a role on an
        aanvraag are a different thing and stay visible to everyone."""
        other = _consultant("Ander", "ander@x.nl")
        ContractPeriod.objects.create(colleague=other, hours_per_week=36, start_date=self.today)
        body = self.client.get(reverse("home"), {"collega": other.public_id}).content.decode()
        assert "36 uur" not in body
        assert "Contracturen" not in body


class ColleaguePanelContractPeriodTest(TestCase):
    """A BDM and an Office assistent read any colleague's periods in the panel,
    and keep them from there: the block asks the rule, not which screen it is on."""

    def setUp(self):
        setup_roles()
        self.client = Client()
        self.today = timezone.now().date()
        self.bdm = User.objects.create(email="bm@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        self.bdm.groups.add(Group.objects.get(name=ROLE_BDM))
        self.admin = User.objects.create(email="admin@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        self.admin.groups.add(Group.objects.get(name=ROLE_OFFICE_ASSISTANT))
        self.client.force_login(self.admin)
        self.colleague = _consultant("Kees Bos", "kees@x.nl")

    def test_panel_lists_only_the_running_and_coming_periods(self):
        """The panel answers "how many hours now, and soon"; the sheet keeps the history."""
        ContractPeriod.objects.create(
            colleague=self.colleague,
            hours_per_week=24,
            start_date=self.today - timedelta(days=400),
            end_date=self.today - timedelta(days=101),
        )
        ContractPeriod.objects.create(
            colleague=self.colleague,
            hours_per_week=36,
            start_date=self.today - timedelta(days=100),
            end_date=self.today + timedelta(days=30),
        )
        ContractPeriod.objects.create(
            colleague=self.colleague, hours_per_week=32, start_date=self.today + timedelta(days=31)
        )
        panel = self.client.get(reverse("home"), {"collega": self.colleague.public_id}).content.decode()
        assert "36 uur" in panel
        assert "32 uur" in panel
        assert "24 uur" not in panel
        sheet = self.client.get(reverse("user-edit", args=[self.colleague.user.public_id])).content.decode()
        assert "24 uur" in sheet

    def test_period_labels_read_running_as_until_today_and_planned_as_from(self):
        ContractPeriod.objects.create(
            colleague=self.colleague, hours_per_week=36, start_date=self.today - timedelta(days=10)
        )
        ContractPeriod.objects.create(
            colleague=self.colleague, hours_per_week=32, start_date=self.today + timedelta(days=10)
        )
        panel = self.client.get(reverse("home"), {"collega": self.colleague.public_id}).content.decode()
        assert f"{date_format(self.today - timedelta(days=10), 'j b Y')} t/m heden" in panel
        assert f"Vanaf {date_format(self.today + timedelta(days=10), 'j b Y')}" in panel

    def test_panel_says_so_when_the_contract_has_ended(self):
        ContractPeriod.objects.create(
            colleague=self.colleague,
            hours_per_week=24,
            start_date=self.today - timedelta(days=400),
            end_date=self.today - timedelta(days=1),
        )
        panel = self.client.get(reverse("home"), {"collega": self.colleague.public_id}).content.decode()
        assert "Geen lopend contract." in panel
        assert "Niet ingevuld" not in panel

    def test_panel_lets_an_office_assistant_keep_the_hours(self):
        """The buttons follow the rule, not the surface: the same block carries
        them in the panel and in the user sheet."""
        ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        body = self.client.get(reverse("home"), {"collega": self.colleague.public_id}).content.decode()
        assert "<h3>Contracturen</h3>" in body
        assert "36 uur" in body
        assert "Contractperiode toevoegen" in body

    def test_panel_lets_a_bdm_keep_the_hours(self):
        """A BDM plans with the hours, so a BDM keeps them, from the panel where
        they already read them."""
        period = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        self.client.force_login(self.bdm)
        body = self.client.get(reverse("home"), {"collega": self.colleague.public_id}).content.decode()
        assert "<h3>Contracturen</h3>" in body
        assert "36 uur" in body
        assert "Contractperiode toevoegen" in body
        url = reverse("contract-period-add", args=[self.colleague.public_id])
        assert self.client.get(url).status_code == 200
        assert self.client.get(reverse("contract-period-delete", args=[period.public_id])).status_code == 200

    def test_an_office_assistant_saves_a_period_for_another_colleague(self):
        url = reverse("contract-period-add", args=[self.colleague.public_id])
        response = self.client.post(url, {"hours_per_week": "36", "start_date": self.today.isoformat(), "end_date": ""})
        assert response.status_code == 200
        body = response.content.decode()
        assert "<h3>Contracturen</h3>" in body
        assert "36 uur" in body
        assert self.colleague.contract_periods.count() == 1

    def _ended_period(self):
        return ContractPeriod.objects.create(
            colleague=self.colleague,
            hours_per_week=24,
            start_date=self.today - timedelta(days=400),
            end_date=self.today - timedelta(days=101),
        )

    def test_the_panel_buttons_carry_the_surface_they_sit_on(self):
        """The two surfaces share the three write routes, so the button says which
        one it is on; the sheet posts back to the url it was opened with."""
        period = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        panel = self.client.get(reverse("home"), {"collega": self.colleague.public_id}).content.decode()
        add_url = reverse("contract-period-add", args=[self.colleague.public_id])
        edit_url = reverse("contract-period-edit", args=[period.public_id])
        delete_url = reverse("contract-period-delete", args=[period.public_id])
        assert f'{add_url}?vanuit=paneel"' in panel
        assert f'{edit_url}?vanuit=paneel"' in panel
        assert f'{delete_url}?vanuit=paneel"' in panel

        sheet = self.client.get(reverse("user-edit", args=[self.colleague.user.public_id])).content.decode()
        assert "vanuit=paneel" not in sheet
        assert f'{add_url}"' in sheet

        # The sheet posts back to the same url, so a validation error and a save
        # both keep the surface.
        opened = self.client.get(add_url + "?vanuit=paneel").content.decode()
        assert f'{add_url}?vanuit=paneel"' in opened
        confirm = self.client.get(delete_url + "?vanuit=paneel").content.decode()
        assert f'{delete_url}?vanuit=paneel"' in confirm

    def test_saving_from_the_panel_swaps_the_panel_slice_back(self):
        """Not the sheet's whole history: the panel leaves ended periods out on
        purpose, and a save must not put them back."""
        self._ended_period()
        panel = self.client.get(reverse("home"), {"collega": self.colleague.public_id}).content.decode()
        assert "24 uur" not in panel

        url = reverse("contract-period-add", args=[self.colleague.public_id])
        form = {"hours_per_week": "36", "start_date": self.today.isoformat(), "end_date": ""}
        body = self.client.post(url + "?vanuit=paneel", form).content.decode()
        assert "36 uur" in body
        assert "24 uur" not in body

    def test_saving_from_the_user_sheet_keeps_the_history(self):
        self._ended_period()
        url = reverse("contract-period-add", args=[self.colleague.public_id])
        form = {"hours_per_week": "36", "start_date": self.today.isoformat(), "end_date": ""}
        body = self.client.post(url, form).content.decode()
        assert "36 uur" in body
        assert "24 uur" in body

    def test_deleting_from_the_panel_swaps_the_panel_slice_back(self):
        """Including the empty text, which differs per surface: the panel says the
        contract has ended where the sheet would say nothing is filled in."""
        ended = self._ended_period()
        period = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        body = self.client.post(
            reverse("contract-period-delete", args=[period.public_id]) + "?vanuit=paneel"
        ).content.decode()
        assert "24 uur" not in body
        assert "Geen lopend contract." in body

        sheet_body = self.client.post(reverse("contract-period-delete", args=[ended.public_id])).content.decode()
        assert "Niet ingevuld" in sheet_body


class ServiceHoursTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()
        self.bdm = User.objects.create(email="bdm@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        self.bdm.groups.add(Group.objects.get(name=ROLE_BDM))
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
        assert "Data engineer · 24 uur" in cards

    def test_a_new_member_starts_at_36_hours(self):
        for kind in ("nieuw-ingevuld", "nieuw-aanvraag"):
            body = self.client.get(
                reverse("home"), {"opdracht": self.assignment.public_id, "teamlid": kind}
            ).content.decode()
            assert re.search(r'<option value="36"[^>]*selected', body), kind

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
    """An Office assistent keeps contract periods on the user sheet (beheer/gebruikers)."""

    def setUp(self):
        setup_roles()
        self.client = Client()
        self.today = timezone.now().date()
        self.admin = User.objects.create(email="admin@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        self.admin.groups.add(Group.objects.get(name=ROLE_OFFICE_ASSISTANT))
        self.client.force_login(self.admin)
        self.user = User.objects.create(
            email="kees@rijksoverheid.nl", first_name="Kees", last_name="Bos", onboarding_completed_at=timezone.now()
        )
        self.colleague = Colleague.objects.create(
            name="Kees Bos", email="kees@rijksoverheid.nl", source="wies", user=self.user
        )
        self.add_url = reverse("contract-period-add", args=[self.colleague.public_id])

    def test_sheet_lists_periods_with_the_actions(self):
        period = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        body = self.client.get(reverse("user-edit", args=[self.user.public_id])).content.decode()
        assert "<h3>Contracturen</h3>" in body
        assert "36 uur" in body
        assert self.add_url in body
        assert reverse("contract-period-edit", args=[period.public_id]) in body
        assert reverse("contract-period-delete", args=[period.public_id]) in body

    def test_admin_adds_a_period_and_gets_the_block_back(self):
        response = self.client.post(
            self.add_url, {"hours_per_week": "36", "start_date": self.today.isoformat(), "end_date": ""}
        )
        assert response.status_code == 200, response.content
        body = response.content.decode()
        assert 'id="contractPeriodMount" hx-swap-oob="innerHTML"' in body
        assert "<h3>Contracturen</h3>" in body
        assert "36 uur" in body
        [period] = self.colleague.contract_periods.all()
        assert (period.hours_per_week, period.start_date) == (36, self.today)

    def test_period_changes_are_logged_on_the_colleague(self):
        before = Event.objects.count()
        self.client.post(self.add_url, {"hours_per_week": "36", "start_date": self.today.isoformat(), "end_date": ""})
        [period] = self.colleague.contract_periods.all()
        self.client.post(
            reverse("contract-period-edit", args=[period.public_id]),
            {"hours_per_week": "24", "start_date": self.today.isoformat(), "end_date": ""},
        )
        self.client.post(reverse("contract-period-delete", args=[period.public_id]))
        events = list(Event.objects.order_by("id")[before:])
        assert [e.context["action"] for e in events] == ["create", "update", "delete"]
        assert all(e.object_type == "Colleague" and e.object_id == self.colleague.id for e in events)
        assert events[1].context["before"]["hours_per_week"] == 36
        assert events[1].context["after"]["hours_per_week"] == 24
        assert events[2].context["before"]["hours_per_week"] == 24
        assert events[2].context["after"] is None

    def test_deleting_asks_first_in_the_shared_modal(self):
        period = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        body = self.client.get(reverse("contract-period-delete", args=[period.public_id])).content.decode()
        assert "Contractperiode verwijderen?" in body
        assert "36 uur" in body
        assert 'text="Verwijder periode"' in body
        assert ContractPeriod.objects.filter(pk=period.pk).exists()

    def test_a_colleague_without_user_still_gets_an_event(self):
        loose = Colleague.objects.create(name="Weg Gebruiker", email="weg@x.nl", source="wies")
        before = Event.objects.count()
        self.client.post(
            reverse("contract-period-add", args=[loose.public_id]),
            {"hours_per_week": "36", "start_date": self.today.isoformat(), "end_date": ""},
        )
        assert Event.objects.count() == before + 1
        event = Event.objects.order_by("-id").first()
        assert (event.object_type, event.object_id) == ("Colleague", loose.id)

    def test_admin_edits_and_deletes_a_period(self):
        period = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        self.client.post(
            reverse("contract-period-edit", args=[period.public_id]),
            {"hours_per_week": "24", "start_date": self.today.isoformat(), "end_date": ""},
        )
        period.refresh_from_db()
        assert period.hours_per_week == 24
        response = self.client.post(reverse("contract-period-delete", args=[period.public_id]))
        assert response.status_code == 200
        assert "Niet ingevuld" in response.content.decode()
        assert not ContractPeriod.objects.filter(pk=period.pk).exists()

    def test_add_sheet_says_what_applies_now_and_starts_from_those_hours(self):
        start = self.today - timedelta(days=100)
        ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=40, start_date=start)
        sheet = self.client.get(self.add_url).content.decode()
        assert f'text="Huidig contract: 40 uur per week, sinds {date_format(start, "j b Y")}"' in sheet
        assert "stopt automatisch op de dag vóór de nieuwe startdatum" in sheet
        assert re.search(r'<option value="40"[^>]*selected', sheet)

    def test_add_sheet_hides_the_end_date_behind_the_switch(self):
        sheet = self.client.get(self.add_url).content.decode()
        assert "Huidig contract" not in sheet
        assert 'label="Einddatum is bekend" data-contract-end-known >' in sheet
        assert '<nldd-form-field label="Einddatum" hidden>' in sheet
        period = ContractPeriod.objects.create(
            colleague=self.colleague, hours_per_week=36, start_date=self.today, end_date=self.today + timedelta(days=9)
        )
        edit = self.client.get(reverse("contract-period-edit", args=[period.public_id])).content.decode()
        assert "data-contract-end-known checked" in edit
        assert '<nldd-form-field label="Einddatum">' in edit

    def test_new_period_ends_the_running_one_the_day_before(self):
        running = ContractPeriod.objects.create(
            colleague=self.colleague, hours_per_week=36, start_date=self.today - timedelta(days=100)
        )
        start = self.today + timedelta(days=7)
        before = Event.objects.count()
        response = self.client.post(
            self.add_url, {"hours_per_week": "32", "start_date": start.isoformat(), "end_date": ""}
        )
        assert response.status_code == 200
        assert "overlapt" not in response.content.decode()
        running.refresh_from_db()
        assert running.end_date == start - timedelta(days=1)
        assert self.colleague.contract_periods.get(start_date=start).hours_per_week == 32
        # Both changes are logged: the ended period and the new one.
        events = list(Event.objects.order_by("id")[before:])
        assert [e.context["action"] for e in events] == ["update", "create"]
        assert events[0].context["after"]["end_date"] == (start - timedelta(days=1)).isoformat()

    def test_ending_the_running_period_never_stretches_it(self):
        running = ContractPeriod.objects.create(
            colleague=self.colleague,
            hours_per_week=36,
            start_date=self.today - timedelta(days=100),
            end_date=self.today + timedelta(days=10),
        )
        start = self.today + timedelta(days=60)
        self.client.post(self.add_url, {"hours_per_week": "32", "start_date": start.isoformat(), "end_date": ""})
        running.refresh_from_db()
        assert running.end_date == self.today + timedelta(days=10)
        assert self.colleague.contract_periods.count() == 2

    def test_a_field_error_leaves_the_banner_on_the_running_period(self):
        # The running period is ended before validation and rolled back after;
        # the banner must render the rolled-back state, not the in-memory one.
        running = ContractPeriod.objects.create(
            colleague=self.colleague, hours_per_week=36, start_date=self.today - timedelta(days=100)
        )
        start = self.today + timedelta(days=10)
        response = self.client.post(
            self.add_url,
            {
                "hours_per_week": "32",
                "start_date": start.isoformat(),
                "end_date": (start - timedelta(days=1)).isoformat(),
            },
        )
        body = response.content.decode()
        assert "Einddatum moet op of na de startdatum liggen" in body
        assert f"sinds {date_format(running.start_date, 'j b Y')}" in body
        assert " t/m " not in body.split("Huidig contract")[1].split('"')[0]
        running.refresh_from_db()
        assert running.end_date is None

    def test_a_new_period_starting_before_the_running_one_still_overlaps(self):
        running = ContractPeriod.objects.create(
            colleague=self.colleague, hours_per_week=36, start_date=self.today - timedelta(days=100)
        )
        response = self.client.post(
            self.add_url,
            {"hours_per_week": "32", "start_date": (self.today - timedelta(days=200)).isoformat(), "end_date": ""},
        )
        assert "overlapt" in response.content.decode()
        running.refresh_from_db()
        assert running.end_date is None
        assert self.colleague.contract_periods.count() == 1

    def test_an_invalid_new_period_does_not_end_the_running_one(self):
        running = ContractPeriod.objects.create(
            colleague=self.colleague, hours_per_week=36, start_date=self.today - timedelta(days=100)
        )
        response = self.client.post(
            self.add_url, {"hours_per_week": "41", "start_date": self.today.isoformat(), "end_date": ""}
        )
        assert response.status_code == 200
        running.refresh_from_db()
        assert running.end_date is None
        assert self.colleague.contract_periods.count() == 1

    def test_user_sheet_saves_from_its_footer(self):
        sheet = self.client.get(reverse("user-edit", args=[self.user.public_id])).content.decode()
        footer = sheet[sheet.index('slot="footer"') :]
        assert 'hx-include="#userForm"' in footer
        assert 'text="Opslaan"' in footer
        # The form itself carries no visible submit button any more.
        form = sheet[sheet.index('id="userForm"') : sheet.index("</form>")]
        assert "<nldd-button" not in form
        assert 'type="submit" hidden' in form

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

    def test_user_without_colleague_gets_no_block(self):
        loose = User.objects.create(email="los@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        body = self.client.get(reverse("user-edit", args=[loose.public_id])).content.decode()
        assert "Contracturen" not in body

    def test_deleting_the_user_ends_the_contract_on_the_chosen_day(self):
        """The colleague outlives the user, so the contract ends on the day the
        beheerder picks; a period planned after that day goes."""
        running = ContractPeriod.objects.create(
            colleague=self.colleague, hours_per_week=36, start_date=self.today - timedelta(days=400)
        )
        planned = ContractPeriod.objects.create(
            colleague=self.colleague, hours_per_week=32, start_date=self.today + timedelta(days=30)
        )
        running.end_date = planned.start_date - timedelta(days=1)
        running.save()
        url = reverse("user-delete", args=[self.user.public_id])
        dialog = self.client.get(url).content.decode()
        assert "Het collegaprofiel blijft bestaan" in dialog
        assert "Lopend contract" in dialog
        assert f'text="36 uur per week" supporting-text="sinds {date_format(running.start_date, "j b Y")}"' in dialog
        assert "Begint later" in dialog
        assert (
            f'text="Contract vanaf {date_format(planned.start_date, "j b Y")}" supporting-text="32 uur per week"'
            in dialog
        )
        assert 'name="left_on"' in dialog

        left_on = self.today - timedelta(days=10)
        response = self.client.post(url, {"left_on": left_on.isoformat()})
        assert response.status_code == 200
        assert "HX-Redirect" in response
        running.refresh_from_db()
        assert running.end_date == left_on
        assert not ContractPeriod.objects.filter(pk=planned.pk).exists()
        assert Colleague.objects.filter(pk=self.colleague.pk).exists()
        event = Event.objects.order_by("-id").first()
        assert event.context["left_on"] == left_on.isoformat()
        assert event.context["contract_ended"]["hours_per_week"] == 36
        assert [p["hours_per_week"] for p in event.context["contract_dropped"]] == [32]

    def test_a_day_before_the_current_period_drops_it_and_ends_the_earlier_one(self):
        """Backdating past a change of hours: the newer period never applied."""
        earlier = ContractPeriod.objects.create(
            colleague=self.colleague,
            hours_per_week=32,
            start_date=self.today - timedelta(days=400),
            end_date=self.today - timedelta(days=101),
        )
        current = ContractPeriod.objects.create(
            colleague=self.colleague, hours_per_week=36, start_date=self.today - timedelta(days=100)
        )
        left_on = self.today - timedelta(days=200)
        self.client.post(reverse("user-delete", args=[self.user.public_id]), {"left_on": left_on.isoformat()})
        earlier.refresh_from_db()
        assert earlier.end_date == left_on
        assert not ContractPeriod.objects.filter(pk=current.pk).exists()
        event = Event.objects.order_by("-id").first()
        assert event.context["contract_ended"]["hours_per_week"] == 32
        assert [p["hours_per_week"] for p in event.context["contract_dropped"]] == [36]
        # The list after the redirect tells what happened.
        listing = self.client.get(reverse("admin-users")).content.decode()
        assert "Kees Bos is verwijderd." in listing

    def test_the_day_is_required_when_there_is_a_colleague(self):
        running = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        response = self.client.post(reverse("user-delete", args=[self.user.public_id]), {"left_on": ""})
        assert response.status_code == 200
        assert "HX-Redirect" not in response
        assert User.objects.filter(pk=self.user.pk).exists()
        running.refresh_from_db()
        assert running.end_date is None

    def test_an_invalid_day_keeps_the_user_and_reopens_the_modal(self):
        response = self.client.post(reverse("user-delete", args=[self.user.public_id]), {"left_on": "gisteren"})
        assert response.status_code == 200
        assert "HX-Redirect" not in response
        assert "data-auto-show" in response.content.decode()
        assert User.objects.filter(pk=self.user.pk).exists()

    def test_deleting_a_user_without_contract_says_nothing_about_it(self):
        body = self.client.get(reverse("user-delete", args=[self.user.public_id])).content.decode()
        assert "blijft bestaan" in body
        assert "Contract eindigt" not in body
        assert "Lopend contract" not in body

    def test_deleting_the_user_ends_running_placements_and_drops_planned_ones(self):
        """Placements follow the contract: a running one ends on the day (with
        its own period, so the opdracht keeps its dates), a planned one goes,
        an ended one stays as it was. The dialog says so beforehand."""
        skill = Skill.objects.create(name="Scrum Master")
        opdracht = Assignment.objects.create(
            name="Lopende klus",
            source="wies",
            start_date=self.today - timedelta(days=100),
            end_date=self.today + timedelta(days=200),
        )
        following = Placement.objects.create(
            colleague=self.colleague,
            service=Service.objects.create(assignment=opdracht, skill=skill, source="wies"),
            period_source="SERVICE",
            source="wies",
        )
        planned = _placement(self.colleague, "Volgende klus", self.today + timedelta(days=30), None)
        done = _placement(
            self.colleague, "Oude klus", self.today - timedelta(days=300), self.today - timedelta(days=200)
        )
        url = reverse("user-delete", args=[self.user.public_id])

        dialog = self.client.get(url).content.decode()
        assert "Lopende plaatsingen" in dialog
        assert 'text="Lopende klus" supporting-text="Scrum Master"' in dialog
        assert (
            f'text="Volgende klus" supporting-text="Plaatsing · vanaf {date_format(planned.start_date, "j b Y")}"'
            in dialog
        )
        assert "Oude klus" not in dialog

        left_on = self.today - timedelta(days=5)
        response = self.client.post(url, {"left_on": left_on.isoformat()})
        assert "HX-Redirect" in response
        following.refresh_from_db()
        assert following.period_source == "PLACEMENT"
        assert (following.start_date, following.end_date) == (opdracht.start_date, left_on)
        opdracht.refresh_from_db()
        assert opdracht.end_date == self.today + timedelta(days=200)
        assert not Placement.objects.filter(pk=planned.pk).exists()
        done.refresh_from_db()
        assert done.end_date == self.today - timedelta(days=200)
        event = Event.objects.order_by("-id").first()
        assert [p["assignment"] for p in event.context["placements_ended"]] == ["Lopende klus"]
        assert [p["assignment"] for p in event.context["placements_dropped"]] == ["Volgende klus"]
        # Each touched opdracht gets the same team event a manual change would,
        # so its timeline says who ended or removed the placement, and when.
        team_events = Event.objects.filter(object_type="Assignment", context__field_name="services")
        assert {e.object_id for e in team_events} == {opdracht.id, planned.service.assignment_id}
        ended_event = team_events.get(object_id=opdracht.id)
        assert ended_event.user == self.admin
        [change] = ended_event.context["changes"]
        assert change["old"]["end_date"] == (self.today + timedelta(days=200)).isoformat()
        assert change["new"]["end_date"] == left_on.isoformat()
        dropped_event = team_events.get(object_id=planned.service.assignment_id)
        [change] = dropped_event.context["changes"]
        assert change["old"]["colleague_name"] == "Kees Bos"
        assert change["new"]["colleague_name"] is None

    def test_a_day_before_a_started_placement_is_refused(self):
        """Backdating past the start of a placement that already ran would drop
        it, and with it the record that the person worked there."""
        placement = _placement(
            self.colleague, "Gelopen klus", self.today - timedelta(days=100), self.today + timedelta(days=100)
        )
        response = self.client.post(
            reverse("user-delete", args=[self.user.public_id]),
            {"left_on": (self.today - timedelta(days=200)).isoformat()},
        )
        assert "HX-Redirect" not in response
        assert "vóór een plaatsing die al is begonnen" in response.content.decode()
        assert Placement.objects.filter(pk=placement.pk).exists()
        assert User.objects.filter(pk=self.user.pk).exists()

    def test_placements_alone_make_the_day_required(self):
        _placement(self.colleague, "Klus", self.today - timedelta(days=10), None)
        response = self.client.post(reverse("user-delete", args=[self.user.public_id]), {"left_on": ""})
        assert "HX-Redirect" not in response
        assert User.objects.filter(pk=self.user.pk).exists()

    def test_a_day_before_every_period_is_refused(self):
        period = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        response = self.client.post(
            reverse("user-delete", args=[self.user.public_id]),
            {"left_on": (self.today - timedelta(days=10)).isoformat()},
        )
        assert response.status_code == 200
        assert "HX-Redirect" not in response
        assert "vóór elke contractperiode" in response.content.decode()
        assert ContractPeriod.objects.filter(pk=period.pk).exists()
        assert User.objects.filter(pk=self.user.pk).exists()

    def test_without_periods_the_day_is_optional(self):
        dialog = self.client.get(reverse("user-delete", args=[self.user.public_id])).content.decode()
        assert "Wordt vastgelegd bij de verwijdering." in dialog
        response = self.client.post(reverse("user-delete", args=[self.user.public_id]))
        assert "HX-Redirect" in response
        assert not User.objects.filter(pk=self.user.pk).exists()

    def test_a_user_without_colleague_is_deleted_without_a_day(self):
        loose = User.objects.create(email="los@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        response = self.client.post(reverse("user-delete", args=[loose.public_id]))
        assert response.status_code == 200
        assert "HX-Redirect" in response
        assert not User.objects.filter(pk=loose.pk).exists()

    def test_unknown_colleague_is_not_found(self):
        assert self.client.get(reverse("contract-period-add", args=[uuid.uuid4()])).status_code == 404


class ServiceHoursPermissionTest(TestCase):
    """The hours of a role follow the assignment's edit rights: the placed
    consultant reads them, and keeps only the description of their role."""

    def setUp(self):
        setup_roles()
        self.today = timezone.now().date()
        self.user = User.objects.create(email="c@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        self.user.groups.add(Group.objects.get(name=ROLE_CONSULTANT))
        self.colleague = Colleague.objects.create(
            name="Con Sultant", email="c@rijksoverheid.nl", source="wies", user=self.user
        )
        self.placement = _placement(self.colleague, "Eigen klus", self.today, self.today + timedelta(days=90), hours=24)
        self.service = self.placement.service
        self.bdm = User.objects.create(email="bm@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        self.bdm.groups.add(Group.objects.get(name=ROLE_BDM))
        owner = Colleague.objects.create(name="Bas BDM", email="bm@rijksoverheid.nl", source="wies", user=self.bdm)
        self.service.assignment.owner = owner
        self.service.assignment.save(update_fields=["owner"])

    def test_placed_consultant_may_not_update_the_hours_of_own_service(self):
        assert not has_permission(Verb.UPDATE, self.service, self.user, ServiceEditables.hours_per_week)
        assert has_permission(Verb.UPDATE, self.service, self.user, ServiceEditables.description)
        assert has_permission(Verb.UPDATE, self.service, self.bdm, ServiceEditables.hours_per_week)

    def test_role_form_of_the_consultant_ignores_posted_hours(self):
        client = Client()
        client.force_login(self.user)
        response = client.post(
            reverse("placement-edit", args=[self.placement.public_id]) + "?veld=skill",
            {
                "description": "Eigen klus, bijgewerkt",
                "hours_per_week": "32",
                "terug_url": f"/?plaatsing={self.placement.public_id}",
            },
        )
        assert response.status_code == 204, response.content
        self.service.refresh_from_db()
        assert (self.service.description, self.service.hours_per_week) == ("Eigen klus, bijgewerkt", 24)

    def test_team_list_offers_the_role_sheet_on_the_own_row_only(self):
        client = Client()
        client.force_login(self.user)
        assignment = self.service.assignment
        edit_link = f"?plaatsing={self.placement.public_id}&bewerken=1&veld=skill"
        body = client.get(reverse("home"), {"opdracht": assignment.public_id}).content.decode()
        assert "Rol wijzigen" in body
        assert edit_link in body
        other = _consultant("Ander", "ander@x.nl")
        client.force_login(other.user)
        body = client.get(reverse("home"), {"opdracht": assignment.public_id}).content.decode()
        assert "Rol wijzigen" not in body

    def test_an_hours_only_edit_leaves_no_trace_on_the_timeline(self):
        # No history is kept of a role's hours (agreed with Patrick, 13 July 2026).
        client = Client()
        client.force_login(self.bdm)
        before = Event.objects.count()
        response = client.post(
            reverse("placement-edit", args=[self.placement.public_id]) + "?veld=skill",
            {
                "description": "Eigen klus",
                "hours_per_week": "32",
                "terug_url": f"/?plaatsing={self.placement.public_id}",
            },
        )
        assert response.status_code == 204, response.content
        self.service.refresh_from_db()
        assert self.service.hours_per_week == 32
        assert Event.objects.count() == before

    def test_hours_of_a_placed_colleague_are_hidden_from_team_mates(self):
        """Team mates see each other's role and description, not the hours; an
        open aanvraag shows its hours to everyone; a BDM sees them all."""
        assignment = self.service.assignment
        mate = _consultant("Team Maat", "maat@x.nl")
        mate_service = Service.objects.create(
            assignment=assignment, description="Maat", source="wies", hours_per_week=16
        )
        Placement.objects.create(
            colleague=mate,
            service=mate_service,
            period_source="PLACEMENT",
            specific_start_date=self.today,
            specific_end_date=self.today + timedelta(days=90),
            source="wies",
        )
        Service.objects.create(assignment=assignment, description="Open", source="wies", hours_per_week=8)
        client = Client()

        client.force_login(self.user)
        team = client.get(reverse("home"), {"opdracht": assignment.public_id}).content.decode()
        assert "24 uur" in team  # own
        assert "16 uur" not in team  # the team mate's
        assert "8 uur" in team  # the aanvraag's
        mate_panel = client.get(
            reverse("home"), {"plaatsing": mate_service.placements.get().public_id}
        ).content.decode()
        assert "Maat" in mate_panel
        assert "16 uur" not in mate_panel

        client.force_login(self.bdm)
        team = client.get(reverse("home"), {"opdracht": assignment.public_id}).content.decode()
        assert "24 uur" in team
        assert "16 uur" in team
        assert "8 uur" in team

    def test_placement_panel_role_form_carries_the_hours_for_the_owner_only(self):
        names = [spec.name for (_, spec, _) in placement_edit_specs(self.placement, self.bdm, only="skill")]
        assert "hours_per_week" in names
        names = [spec.name for (_, spec, _) in placement_edit_specs(self.placement, self.user, only="skill")]
        assert "hours_per_week" not in names
        assert "description" in names
        client = Client()
        client.force_login(self.user)
        body = client.get(reverse("home"), {"plaatsing": self.placement.public_id}).content.decode()
        assert "24 uur" in body


@override_settings(STAFF_EMAILS=[STAFF_EMAIL])
class ApplicationAdministrationHoursTest(TestCase):
    """Application administration runs the platform and carries nothing
    functional, and hours are as functional as data gets. It is the one authority
    that reaches the user sheet without a role, so it is also the only one for
    which "who sees the block" and "on which screen" can come apart.

    Whoever does platform work and plans with people holds a role for the second
    half; ``rijksauth/0012`` hands the addresses in ``STAFF_EMAILS`` both roles
    once.
    """

    def setUp(self):
        setup_roles()
        self.staff = make_staff_user()
        self.client = Client()
        self.client.force_login(self.staff)
        self.today = timezone.now().date()
        self.colleague = _consultant("Kees Bos", "kees@rijksoverheid.nl")
        self.period = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)

    def test_neither_rule_names_it(self):
        assert has_permission(Verb.READ, self.period, self.staff) is False
        assert has_permission(Verb.UPDATE, self.period, self.staff) is False

    def test_the_colleague_panel_carries_no_block(self):
        body = self.client.get(reverse("home"), {"collega": self.colleague.public_id}).content.decode()

        assert self.colleague.name in body
        assert "Contracturen" not in body

    def test_the_user_sheet_it_opens_for_the_roles_carries_no_block(self):
        """The surface that made this worth pinning: ``user_edit`` opens on
        ``may_administer_roles``, so this sheet renders for someone the hours rule
        says nothing about."""
        body = self.client.get(reverse("user-edit", args=[self.colleague.user.public_id])).content.decode()

        assert "Rollen" in body
        assert "Contracturen" not in body

    def test_the_hours_on_a_colleagues_role_are_not_for_it_either(self):
        """``can_view_role_hours`` is the same authority asked about the other kind
        of hours, so it answers the same."""
        placement = _placement(self.colleague, "Klus", self.today, self.today + timedelta(days=90), hours=16)

        assert can_view_role_hours(self.staff, placement) is False
        body = self.client.get(reverse("home"), {"opdracht": placement.service.assignment.public_id}).content.decode()
        assert "16 uur" not in body


class RoleHoursForUserAdministrationTest(TestCase):
    """The authority ``can_view_role_hours`` names beside the BDM role and the
    placed colleague: whoever administers users (``rijksauth.change_user``, held
    by Office assistent).

    It is the audience this split added to these hours. An Office assistent is
    placed nowhere and holds no BDM role, so without that branch of the predicate
    they read the page a team mate gets, with the hours blanked.
    """

    def setUp(self):
        setup_roles()
        self.today = timezone.now().date()
        self.office_assistant = User.objects.create(
            email="office@rijksoverheid.nl", onboarding_completed_at=timezone.now()
        )
        self.office_assistant.groups.add(Group.objects.get(name=ROLE_OFFICE_ASSISTANT))
        self.colleague = _consultant("Kees Bos", "kees@x.nl")
        self.placement = _placement(self.colleague, "Klus", self.today, self.today + timedelta(days=90), hours=16)

    def test_the_predicate_names_user_administration(self):
        assert can_view_role_hours(self.office_assistant, self.placement) is True

    def test_the_team_list_prints_the_hours_of_a_colleagues_role(self):
        """The surface the predicate feeds: without the branch the row renders
        without its hours, which is what a team mate sees."""
        client = Client()
        client.force_login(self.office_assistant)

        body = client.get(reverse("home"), {"opdracht": self.placement.service.assignment.public_id}).content.decode()

        assert "Kees Bos" in body
        assert "16 uur" in body


class ContractHoursAudienceTest(TestCase):
    """The two contract-hours rules against each other."""

    def setUp(self):
        setup_roles()
        self.colleague = Colleague.objects.create(name="Cora", email="cora@x.nl", source="wies")
        self.period = ContractPeriod.objects.create(
            colleague=self.colleague, hours_per_week=36, start_date=timezone.now().date()
        )

    def test_whoever_may_keep_the_hours_may_read_them(self):
        """What ``_contract_block`` rests on: it returns nothing to a non-reader,
        and the add/edit/delete routes render it after a save on the UPDATE right
        alone. A role that could write without reading would get an empty block
        swapped back in.
        """
        keepers = []
        for role in (ROLE_BDM, ROLE_OFFICE_ASSISTANT, ROLE_CONSULTANT):
            user = User.objects.create(email=f"{role}@rijksoverheid.nl", onboarding_completed_at=timezone.now())
            user.groups.add(Group.objects.get(name=role))
            if has_permission(Verb.UPDATE, self.period, user):
                keepers.append(role)
                with self.subTest(role=role):
                    assert has_permission(Verb.READ, self.period, user) is True

        # The assertion above only runs for a role that reached UPDATE, so a rule
        # granting it to nobody would leave every branch unentered and the loop silent.
        assert keepers, "No role reached UPDATE, so the loop above asserted nothing."
