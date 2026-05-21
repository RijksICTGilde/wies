import zoneinfo
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from wies.rijksauth.models import AuthEvent
from wies.rijksauth.services.usage import DAILY_WINDOW_DAYS, get_usage_stats

User = get_user_model()
AMS = zoneinfo.ZoneInfo("Europe/Amsterdam")
UTC = zoneinfo.ZoneInfo("UTC")


def make_event(name: str, email: str, timestamp: datetime) -> AuthEvent:
    event = AuthEvent.objects.create(name=name, user_email=email)
    AuthEvent.objects.filter(pk=event.pk).update(timestamp=timestamp)
    event.refresh_from_db()
    return event


class GetUsageStatsTest(TestCase):
    def setUp(self):
        self.now = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)

    def test_empty_database(self):
        stats = get_usage_stats(now=self.now)

        assert stats["mau"] == 0
        assert stats["wau"] == 0
        assert stats["total_ever"] == 0
        assert stats["total_logins_90d"] == 0
        assert stats["failures_30d"] == 0
        assert stats["max_daily"] == 0
        assert len(stats["daily_logins"]) == DAILY_WINDOW_DAYS
        assert all(count == 0 for _, count in stats["daily_logins"])

    def test_distinct_users_for_mau_and_wau(self):
        User.objects.create_user(email="a@rijksoverheid.nl")
        User.objects.create_user(email="b@rijksoverheid.nl")

        # Two events for a@ in last 7d, one event for b@ in last 7d.
        make_event("Login.success", "a@rijksoverheid.nl", self.now - timedelta(days=1))
        make_event("Login.success", "a@rijksoverheid.nl", self.now - timedelta(days=2))
        make_event("Login.success", "b@rijksoverheid.nl", self.now - timedelta(days=3))
        # Older event for a@ — outside WAU but inside MAU.
        make_event("Login.success", "a@rijksoverheid.nl", self.now - timedelta(days=20))

        stats = get_usage_stats(now=self.now)

        assert stats["wau"] == 2
        assert stats["mau"] == 2
        assert stats["total_ever"] == 2

    def test_login_fail_does_not_count_as_active(self):
        User.objects.create_user(email="a@rijksoverheid.nl")
        make_event("Login.fail", "a@rijksoverheid.nl", self.now - timedelta(days=1))

        stats = get_usage_stats(now=self.now)

        assert stats["mau"] == 0
        assert stats["wau"] == 0
        assert stats["total_ever"] == 0
        assert stats["failures_30d"] == 1
        assert stats["max_daily"] == 0

    def test_offboarded_user_counted_in_mau_and_total_ever(self):
        # One current user, plus an event from a since-deleted user.
        User.objects.create_user(email="a@rijksoverheid.nl")
        make_event("Login.success", "a@rijksoverheid.nl", self.now - timedelta(days=1))
        make_event("Login.success", "offboarded@rijksoverheid.nl", self.now - timedelta(days=5))

        stats = get_usage_stats(now=self.now)

        # MAU and total_ever count the offboarded email — these are event-based, not user-table-based.
        assert stats["mau"] == 2
        assert stats["wau"] == 2
        assert stats["total_ever"] == 2

    def test_daily_logins_zero_filled_and_ordered(self):
        User.objects.create_user(email="a@rijksoverheid.nl")
        # Three logins on the same local day, one on a different day.
        same_day = self.now - timedelta(days=2)
        make_event("Login.success", "a@rijksoverheid.nl", same_day)
        make_event("Login.success", "a@rijksoverheid.nl", same_day + timedelta(hours=1))
        make_event("Login.success", "a@rijksoverheid.nl", same_day + timedelta(hours=2))
        make_event("Login.success", "a@rijksoverheid.nl", self.now - timedelta(days=10))
        # A login outside the 90d window — must not be counted in total_logins_90d.
        make_event("Login.success", "a@rijksoverheid.nl", self.now - timedelta(days=120))

        stats = get_usage_stats(now=self.now)
        daily = stats["daily_logins"]

        assert len(daily) == DAILY_WINDOW_DAYS
        # Ordered oldest first.
        days = [d for d, _ in daily]
        assert days == sorted(days)
        # Sum equals total Login.success inside the 90d window.
        assert sum(c for _, c in daily) == 4
        assert stats["max_daily"] == 3
        assert stats["total_logins_90d"] == 4

    def test_daily_bucketing_uses_amsterdam_timezone(self):
        User.objects.create_user(email="a@rijksoverheid.nl")
        # 2026-05-04 23:30 Europe/Amsterdam — local day 2026-05-04.
        # In UTC that's 2026-05-04 21:30 (Amsterdam is UTC+2 in May).
        local_late_evening = datetime(2026, 5, 4, 23, 30, tzinfo=AMS)
        make_event("Login.success", "a@rijksoverheid.nl", local_late_evening)

        stats = get_usage_stats(now=self.now)
        non_zero_days = [(d, c) for d, c in stats["daily_logins"] if c > 0]

        assert non_zero_days == [(local_late_evening.date(), 1)]
