"""Audit trail for contract-period changes."""

from wies.core.services.events import create_event


def contract_period_event(request, period, action, before=None):
    """Logs a contract-period change on the colleague the hours belong to.

    On the colleague, not the user: the colleague outlives the user, and the
    hours of someone who has left are exactly what must stay traceable. Nothing
    displays these events yet.
    """
    after = None if action == "delete" else contract_period_snapshot(period)
    create_event(
        object_type="Colleague",
        action="update",
        source="user",
        object_id=period.colleague_id,
        user=request.user,
        request=request,
        context={"field_name": "contract_periods", "action": action, "before": before, "after": after},
    )


def contract_period_snapshot(period):
    return {
        "hours_per_week": period.hours_per_week,
        "start_date": period.start_date.isoformat(),
        "end_date": period.end_date.isoformat() if period.end_date else None,
    }
