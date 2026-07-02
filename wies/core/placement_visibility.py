"""Shared rule for who may see a placement and the privacy note to show.

A placement that is *currently active* (started and not yet ended) is visible to
everyone. A placement that is *ended* or *not yet started* (future) is private:
only the placed colleague and the assignment's BM-owner may see it, each with a
note. Used by the opdracht side panel, the placement detail panel and the
colleague profile so the rule stays identical across surfaces.
"""

from dataclasses import dataclass

PRIVACY_OWN = "Alleen zichtbaar voor jou en de Business Manager"
PRIVACY_BM = "Alleen zichtbaar voor jou en de consultant"

# Chip labels per timing, for the non-active states.
LABELS = {"ended": "Afgelopen", "future": "Gepland"}


@dataclass(frozen=True)
class PlacementVisibility:
    visible: bool  # may the viewer see this placement at all?
    timing: str  # "active" | "ended" | "future"
    privacy_note: str | None  # set only for a visible non-active placement


def placement_timing(start, end, today) -> str:
    if start is not None and start > today:
        return "future"
    if end is not None and end < today:
        return "ended"
    return "active"


def evaluate(start, end, placed_colleague_id, viewer, viewer_is_bm, today) -> PlacementVisibility:
    """Decide visibility for one placement. ``viewer`` is the viewing Colleague
    (or None); ``viewer_is_bm`` whether they own the assignment."""
    timing = placement_timing(start, end, today)
    if timing == "active":
        return PlacementVisibility(visible=True, timing=timing, privacy_note=None)
    if viewer is not None and viewer.id == placed_colleague_id:
        return PlacementVisibility(visible=True, timing=timing, privacy_note=PRIVACY_OWN)
    if viewer_is_bm:
        return PlacementVisibility(visible=True, timing=timing, privacy_note=PRIVACY_BM)
    return PlacementVisibility(visible=False, timing=timing, privacy_note=None)
