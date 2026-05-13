import zoneinfo
from datetime import date, datetime, timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from wies.rijksauth.models import AuthEvent

DASHBOARD_TZ = zoneinfo.ZoneInfo("Europe/Amsterdam")
DAILY_WINDOW_DAYS = 90
MAU_DAYS = 30
WAU_DAYS = 7
FAILURES_DAYS = 30


def get_usage_stats(now: datetime | None = None) -> dict:
    if now is None:
        now = timezone.now()

    success = AuthEvent.objects.filter(name="Login.success")

    mau_cutoff = now - timedelta(days=MAU_DAYS)
    wau_cutoff = now - timedelta(days=WAU_DAYS)

    mau = success.filter(timestamp__gte=mau_cutoff).values("user_email").distinct().count()
    wau = success.filter(timestamp__gte=wau_cutoff).values("user_email").distinct().count()

    total_ever = success.values("user_email").distinct().count()

    failures_cutoff = now - timedelta(days=FAILURES_DAYS)
    failures_30d = AuthEvent.objects.filter(name="Login.fail", timestamp__gte=failures_cutoff).count()

    today_local: date = now.astimezone(DASHBOARD_TZ).date()
    daily_start_local = today_local - timedelta(days=DAILY_WINDOW_DAYS - 1)
    daily_cutoff_utc = datetime.combine(daily_start_local, datetime.min.time(), tzinfo=DASHBOARD_TZ)

    rows = (
        success.filter(timestamp__gte=daily_cutoff_utc)
        .annotate(day=TruncDate("timestamp", tzinfo=DASHBOARD_TZ))
        .values("day")
        .annotate(c=Count("id"))
    )
    counts_by_day: dict[date, int] = {row["day"]: row["c"] for row in rows}

    daily_logins: list[tuple[date, int]] = [
        (daily_start_local + timedelta(days=i), counts_by_day.get(daily_start_local + timedelta(days=i), 0))
        for i in range(DAILY_WINDOW_DAYS)
    ]
    max_daily = max((c for _, c in daily_logins), default=0)
    total_logins_90d = sum(c for _, c in daily_logins)

    return {
        "mau": mau,
        "wau": wau,
        "total_ever": total_ever,
        "total_logins_90d": total_logins_90d,
        "failures_30d": failures_30d,
        "daily_logins": daily_logins,
        "max_daily": max_daily,
    }
