"""Shared rule for who may see a placement and the privacy note to show.

A currently active placement is visible to everyone; an ended or future one is
private to the placed colleague and the Business Managers (the BDM role), each
with a note. Shared by the assignment panel, the placement panel and the
colleague profile so the rule stays identical across surfaces.
"""

from dataclasses import dataclass

# Shown to the placed colleague on their own ended/future placement.
PRIVACY_OWN = "Alleen zichtbaar voor jou en de Business Managers"
# Shown to a Business Manager (BDM) who sees the row purely by role, not because
# they are placed on it — hence no "jou": they need not be on the team. Also used
# for an ended assignment shown on a colleague profile, where the audience is the
# same.
PRIVACY_BDM = "Alleen zichtbaar voor de Business Managers en het team"

# Chip labels per timing, for the non-active states.
LABELS = {"ended": "Afgelopen", "future": "Gepland"}


@dataclass(frozen=True)
class PlacementVisibility:
    visible: bool
    timing: str  # "active" | "ended" | "future"
    privacy_note: str | None  # Set only for a visible non-active placement.


def placement_timing(start, end, today) -> str:
    if start is not None and start > today:
        return "future"
    if end is not None and end < today:
        return "ended"
    return "active"


def evaluate_placement_visibility(start, end, placed_colleague_id, viewer, viewer_is_bdm, today) -> PlacementVisibility:
    """Decides visibility for one placement.

    A non-active placement is visible to the placed colleague (``PRIVACY_OWN``)
    and to any Business Manager (``viewer_is_bdm``, ``PRIVACY_BDM``). The
    placed-colleague check runs first, so a placed colleague who is also a BDM
    keeps the more specific ``PRIVACY_OWN`` note.
    """
    timing = placement_timing(start, end, today)
    if timing == "active":
        return PlacementVisibility(visible=True, timing=timing, privacy_note=None)
    if viewer is not None and viewer.id == placed_colleague_id:
        return PlacementVisibility(visible=True, timing=timing, privacy_note=PRIVACY_OWN)
    if viewer_is_bdm:
        return PlacementVisibility(visible=True, timing=timing, privacy_note=PRIVACY_BDM)
    return PlacementVisibility(visible=False, timing=timing, privacy_note=None)
