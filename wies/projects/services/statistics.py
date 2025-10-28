from datetime import date


def get_weeks_remaining(assignment):
    # Calculate weeks until end
    weeks_remaining = None
    if assignment.end_date:
        today = date.today()
        if assignment.end_date > today:
            delta = assignment.end_date - today
            weeks_remaining = round(delta.days / 7)
        else:
            weeks_remaining = 0
    return weeks_remaining
