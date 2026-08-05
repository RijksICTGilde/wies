"""Tests for the Prognose forecast (``capacity_forecast``): capacity vs. the
planned + aanvragen demand, and that demand can exceed capacity."""

from datetime import date, timedelta

from django.test import TestCase

from wies.core.models import Assignment, Colleague, ContractPeriod, Placement, Service
from wies.core.services.occupancy import capacity_forecast


class CapacityForecastTest(TestCase):
    def setUp(self):
        self.today = date(2026, 8, 5)
        # Window covering the whole horizon so every week is "covered".
        self.start = self.today - timedelta(days=200)
        self.end = self.today + timedelta(days=400)

        # One colleague with a single open-ended contract of 40 u/wk = capacity.
        self.colleague = Colleague.objects.create(name="Cap Aciteit", email="ca@rijksoverheid.nl", source="wies")
        ContractPeriod.objects.create(colleague=self.colleague, hours_per_week=40, start_date=self.start)

        self.assignment = Assignment.objects.create(
            name="Opdracht", source="wies", start_date=self.start, end_date=self.end
        )

    def _service(self, hours, *, filled):
        service = Service.objects.create(
            assignment=self.assignment, description="rol", source="wies", assignment_hours_per_week=hours
        )
        if filled:
            Placement.objects.create(colleague=self.colleague, service=service, source="wies")
        return service

    def test_series_present_and_lengths_match(self):
        self._service(20, filled=True)
        forecast = capacity_forecast(self.today)
        n = len(forecast["weeks"])
        assert n > 0
        for key in ("capacity", "planned", "aanvragen", "unfilled", "overcommit"):
            assert len(forecast[key]) == n

    def test_filled_counts_as_planned_open_counts_as_aanvraag(self):
        self._service(20, filled=True)  # ingepland
        self._service(30, filled=False)  # aanvraag
        forecast = capacity_forecast(self.today)
        i = forecast["today_index"]
        assert forecast["planned"][i] == 20
        assert forecast["aanvragen"][i] == 30

    def test_demand_can_exceed_capacity(self):
        # Capacity is 40; a 30u placement + a 30u aanvraag = 60 demand > 40.
        self._service(30, filled=True)
        self._service(30, filled=False)
        forecast = capacity_forecast(self.today)
        i = forecast["today_index"]
        assert forecast["planned"][i] + forecast["aanvragen"][i] > forecast["capacity"][i]
        assert forecast["overcommit"][i] == 20
        assert forecast["unfilled"][i] == 0

    def test_slack_reported_as_unfilled_no_overcommit(self):
        self._service(10, filled=True)  # 10 of 40 used
        forecast = capacity_forecast(self.today)
        i = forecast["today_index"]
        assert forecast["unfilled"][i] == 30
        assert forecast["overcommit"][i] == 0
