"""Shared rule for who may see a placement and the privacy note to show.

A currently active placement is visible to everyone; an ended or future one is
private to the placed colleague and the assignment's BM-owner, each with a note.
Shared by the assignment panel, the placement panel and the colleague profile so
the rule stays identical across surfaces.
"""

from dataclasses import dataclass

PRIVACY_OWN = "Alleen zichtbaar voor jou en de Business Manager"
PRIVACY_BM = "Alleen zichtbaar voor jou en de consultant"
# For a past assignment the viewer owned as BM but was not placed on: the note
# covers the whole team, not one consultant. Kept beside the other wordings
# rather than in the view, so all variants stay together.
PRIVACY_TEAM = "Alleen zichtbaar voor jou en het team"

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


def evaluate_placement_visibility(start, end, placed_colleague_id, viewer, owner_id, today) -> PlacementVisibility:
    """Decides visibility for one placement.

    ``viewer`` is the viewing Colleague (or None); ``owner_id`` is the id of the
    assignment's BM-owner. Whether the viewer is the BM is derived here, so the
    caller passes identities and this function owns the rule.
    """
    timing = placement_timing(start, end, today)
    if timing == "active":
        return PlacementVisibility(visible=True, timing=timing, privacy_note=None)
    if viewer is not None and viewer.id == placed_colleague_id:
        return PlacementVisibility(visible=True, timing=timing, privacy_note=PRIVACY_OWN)
    if viewer is not None and owner_id is not None and viewer.id == owner_id:
        return PlacementVisibility(visible=True, timing=timing, privacy_note=PRIVACY_BM)
    return PlacementVisibility(visible=False, timing=timing, privacy_note=None)
