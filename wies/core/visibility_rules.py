"""Shared rules for who may see a row and the privacy note to show.

Two rules over shared primitives (the ``Visibility`` result and ``period_timing``):

- ``evaluate_placement_visibility`` — a currently active placement is visible to
  everyone; an ended or future one is private to the placed colleague and to
  privileged viewers (the Business Managers — the BDM role — and support staff),
  each with a note.
- ``evaluate_assignment_visibility`` — an assignment a colleague *owns* as
  Business Manager: active and not-yet-started ones are public, an ended one is
  shown only to privileged viewers.

Shared by the assignment panel, the placement panel and the colleague profile so
each rule stays identical across surfaces.
"""

from dataclasses import dataclass

from wies.core.roles import is_bdm_or_staff, is_staff_member

# Shown to the placed colleague on their own ended/future placement.
PRIVACY_OWN = "Alleen zichtbaar voor jou en de Business Managers"
# Shown to a Business Manager (BDM) who sees a placement purely by role, not
# because they are placed on it — hence no "jou". The audience is the same as
# PRIVACY_OWN seen from the other side: the placed consultant and the Business
# Managers.
PRIVACY_BDM = "Alleen zichtbaar voor de consultant en de Business Managers"
# Shown on an ended assignment a colleague *owns* as Business Manager (no
# consultant is placed on the row, so PRIVACY_BDM's "de consultant" would not
# fit). Only Business Managers see it.
PRIVACY_BM_OWNED = "Alleen zichtbaar voor de Business Managers"

# Chip labels per timing, for the non-active states.
LABELS = {"ended": "Afgelopen", "future": "Gepland"}


def show_bm_page(request) -> bool:
    """Whether to show the "Business management" section: BDM or support staff."""
    return is_bdm_or_staff(request)


def show_staff_pages(request) -> bool:
    """Whether to show the staff-only pages (Statistieken, Database)."""
    user = getattr(request, "user", None)
    return user is not None and is_staff_member(user)


@dataclass(frozen=True)
class Visibility:
    visible: bool
    timing: str  # "active" | "ended" | "future"
    privacy_note: str | None  # Set only for a visible non-active row.


def period_timing(start, end, today) -> str:
    if start is not None and start > today:
        return "future"
    if end is not None and end < today:
        return "ended"
    return "active"


def evaluate_placement_visibility(start, end, placed_colleague_id, request, today) -> Visibility:
    """Decides visibility for one placement, for the request's viewer.

    A non-active placement is visible to the placed colleague (``PRIVACY_OWN``)
    and to a privileged viewer — a Business Manager or support staff
    (``PRIVACY_BDM``). The placed-colleague check runs first, so a placed
    colleague who is also privileged keeps the more specific ``PRIVACY_OWN``
    note.
    """
    timing = period_timing(start, end, today)
    if timing == "active":
        return Visibility(visible=True, timing=timing, privacy_note=None)
    viewer = getattr(getattr(request, "user", None), "colleague", None)
    if viewer is not None and viewer.id == placed_colleague_id:
        return Visibility(visible=True, timing=timing, privacy_note=PRIVACY_OWN)
    if is_bdm_or_staff(request):
        return Visibility(visible=True, timing=timing, privacy_note=PRIVACY_BDM)
    return Visibility(visible=False, timing=timing, privacy_note=None)


def evaluate_assignment_visibility(start, end, request, today) -> Visibility:
    """Decides visibility for one owned (BM-role) assignment, for the request's viewer.

    An active or not-yet-started assignment is public. An ended one is visible
    only to a privileged viewer — a Business Manager or support staff
    (``PRIVACY_BM_OWNED``). Unlike a placement there is no placed consultant, so
    no ``PRIVACY_OWN`` branch and the owner gets no special visibility; the gate
    is purely the role. A future (planned) owned assignment is treated as public,
    matching the profile's long-standing behaviour.
    """
    timing = period_timing(start, end, today)
    if timing != "ended":
        return Visibility(visible=True, timing=timing, privacy_note=None)
    if is_bdm_or_staff(request):
        return Visibility(visible=True, timing=timing, privacy_note=PRIVACY_BM_OWNED)
    return Visibility(visible=False, timing=timing, privacy_note=None)
