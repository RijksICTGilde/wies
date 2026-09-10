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
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from wies.core.editables.service import ServiceEditables
from wies.core.models import Assignment, Colleague, ContractPeriod, Placement, Service, Skill
from wies.core.permission_engine import Verb, has_permission
from wies.core.roles import setup_roles
from wies.core.services.occupancy import BUCKET_FULL, BUCKET_PARTIAL, colleague_occupancy, occupancy_summary
from wies.core.services.placements import placement_edit_specs

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
    """A consultant reads their own periods on the profile; a BDM keeps their own."""

    def setUp(self):
        setup_roles()
        self.client = Client()
        self.today = timezone.now().date()
        self.user = User.objects.create(email="me@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        self.user.groups.add(Group.objects.get(name="Consultant"))
        self.colleague = Colleague.objects.create(
            name="Ik Zelf", email="me@rijksoverheid.nl", source="wies", user=self.user
        )
        self.client.force_login(self.user)
        self.add_url = reverse("contract-period-add", args=[self.colleague.public_id]) + "?in=profile"

    def _make_bdm(self):
        self.user.groups.add(Group.objects.get(name="Business Development Manager"))

    def test_consultant_sees_own_periods_without_buttons(self):
        ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        body = self.client.get(reverse("user-profile")).content.decode()
        assert "36 uur" in body
        assert "Contractperiode toevoegen" not in body
        assert "Verwijderen" not in body

    def test_consultant_without_periods_is_pointed_to_the_business_manager(self):
        body = self.client.get(reverse("user-profile")).content.decode()
        assert "Je business manager kan je contracturen invullen" in body

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

    def test_bdm_profile_offers_to_add(self):
        self._make_bdm()
        body = self.client.get(reverse("user-profile")).content.decode()
        assert "Contractperiode toevoegen" in body
        assert self.add_url in body

    def test_add_sheet_saves_a_period(self):
        self._make_bdm()
        response = self.client.post(
            self.add_url, {"hours_per_week": "32", "start_date": self.today.isoformat(), "end_date": ""}
        )
        assert response.status_code == 200
        # The sheet closes through its emptied mount; the block comes back refreshed
        # in the profile's shape.
        body = response.content.decode()
        assert 'id="contractPeriodMount" hx-swap-oob="innerHTML"' in body
        assert re.search(r'id="contractPeriodsBlock"\s+hx-swap-oob="outerHTML"', body)
        assert "<h2>Contracturen</h2>" in body
        assert "32 uur" in body
        [period] = ContractPeriod.objects.filter(colleague=self.colleague)
        assert (period.hours_per_week, period.start_date, period.end_date) == (32, self.today, None)

    def test_overlap_comes_back_as_a_field_error(self):
        self._make_bdm()
        ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        response = self.client.post(
            self.add_url, {"hours_per_week": "32", "start_date": self.today.isoformat(), "end_date": ""}
        )
        assert response.status_code == 200
        assert "overlapt" in response.content.decode()
        assert ContractPeriod.objects.count() == 1

    def test_edit_and_delete_own_period(self):
        self._make_bdm()
        period = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        self.client.post(
            reverse("contract-period-edit", args=[period.public_id]) + "?in=profile",
            {"hours_per_week": "24", "start_date": self.today.isoformat(), "end_date": ""},
        )
        period.refresh_from_db()
        assert period.hours_per_week == 24
        response = self.client.post(reverse("contract-period-delete", args=[period.public_id]) + "?in=profile")
        assert response.status_code == 200
        assert "Nog niet ingevuld" in response.content.decode()
        assert not ContractPeriod.objects.filter(pk=period.pk).exists()

    def test_colleague_panel_shows_current_contract_hours_as_a_tag(self):
        ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        body = self.client.get(reverse("home"), {"collega": self.colleague.public_id}).content.decode()
        assert "36 uur" in body
        assert "Contractperiode toevoegen" not in body


class ColleaguePanelContractPeriodTest(TestCase):
    """A BDM keeps the periods of any colleague from the colleague panel."""

    def setUp(self):
        setup_roles()
        self.client = Client()
        self.today = timezone.now().date()
        self.bdm = User.objects.create(email="bm@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        self.bdm.groups.add(Group.objects.get(name="Business Development Manager"))
        self.client.force_login(self.bdm)
        self.colleague = _consultant("Kees Bos", "kees@x.nl")

    def test_panel_shows_the_block_instead_of_the_tag(self):
        ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        body = self.client.get(reverse("home"), {"collega": self.colleague.public_id}).content.decode()
        assert "<h3>Contracturen</h3>" in body
        assert "Contractperiode toevoegen" in body
        assert 'icon="clock"' not in body

    def test_save_from_the_panel_comes_back_in_panel_shape(self):
        url = reverse("contract-period-add", args=[self.colleague.public_id]) + "?in=panel"
        response = self.client.post(url, {"hours_per_week": "36", "start_date": self.today.isoformat(), "end_date": ""})
        assert response.status_code == 200
        body = response.content.decode()
        assert "<h3>Contracturen</h3>" in body
        assert "36 uur" in body
        assert self.colleague.contract_periods.count() == 1


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
        self.add_url = reverse("contract-period-add", args=[self.colleague.public_id]) + "?in=user"

    def test_sheet_lists_periods_with_the_actions(self):
        period = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        body = self.client.get(reverse("user-edit", args=[self.user.public_id])).content.decode()
        assert "<h3>Contracturen</h3>" in body
        assert "36 uur" in body
        assert self.add_url in body
        assert reverse("contract-period-edit", args=[period.public_id]) + "?in=user" in body
        assert reverse("contract-period-delete", args=[period.public_id]) + "?in=user" in body

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

    def test_admin_edits_and_deletes_a_period(self):
        period = ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=36, start_date=self.today)
        self.client.post(
            reverse("contract-period-edit", args=[period.public_id]) + "?in=user",
            {"hours_per_week": "24", "start_date": self.today.isoformat(), "end_date": ""},
        )
        period.refresh_from_db()
        assert period.hours_per_week == 24
        response = self.client.post(reverse("contract-period-delete", args=[period.public_id]) + "?in=user")
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
        assert "Het collegaprofiel blijft bestaan, met de plaatsingen op opdrachten." in dialog
        assert "De contractperiode van 36 uur eindigt op de dag hieronder." in dialog
        assert 'name="left_on"' in dialog

        left_on = self.today - timedelta(days=10)
        response = self.client.post(url, {"left_on": left_on.isoformat()})
        assert response.status_code == 200
        assert "HX-Redirect" in response
        running.refresh_from_db()
        assert running.end_date == left_on
        assert not ContractPeriod.objects.filter(pk=planned.pk).exists()
        assert Colleague.objects.filter(pk=self.colleague.pk).exists()
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
        assert "Het collegaprofiel blijft bestaan" in body
        assert "contractperiode van" not in body

    def test_unknown_colleague_is_not_found(self):
        assert self.client.get(reverse("contract-period-add", args=[uuid.uuid4()])).status_code == 404


class ServiceHoursPermissionTest(TestCase):
    """The consultant on a service keeps its hours, like its description."""

    def setUp(self):
        setup_roles()
        self.today = timezone.now().date()
        self.user = User.objects.create(email="c@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        self.user.groups.add(Group.objects.get(name="Consultant"))
        self.colleague = Colleague.objects.create(
            name="Con Sultant", email="c@rijksoverheid.nl", source="wies", user=self.user
        )
        self.placement = _placement(self.colleague, "Eigen klus", self.today, self.today + timedelta(days=90), hours=24)
        self.service = self.placement.service

    def test_placed_consultant_may_update_hours_of_own_service(self):
        assert has_permission(Verb.UPDATE, self.service, self.user, ServiceEditables.hours_per_week)
        other = _consultant("Ander", "ander@x.nl")
        theirs = _placement(other, "Andermans klus", self.today, self.today + timedelta(days=90), hours=24).service
        assert not has_permission(Verb.UPDATE, theirs, self.user, ServiceEditables.hours_per_week)

    def test_placed_consultant_saves_hours_from_the_role_form(self):
        client = Client()
        client.force_login(self.user)
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

    def test_placement_panel_role_form_carries_the_hours(self):
        names = [spec.name for (_, spec, _) in placement_edit_specs(self.placement, self.user, only="skill")]
        assert "hours_per_week" in names
        client = Client()
        client.force_login(self.user)
        body = client.get(reverse("home"), {"plaatsing": self.placement.public_id}).content.decode()
        assert "24 uur" in body
