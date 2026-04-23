"""Explicit model_label → EditableSet mapping for runtime dispatch."""

from typing import TYPE_CHECKING

from wies.core.inline_edit.editables.assignment import AssignmentEditables
from wies.core.inline_edit.editables.colleague import ColleagueEditables
from wies.core.inline_edit.editables.placement import PlacementEditables
from wies.core.inline_edit.editables.service import ServiceEditables
from wies.core.inline_edit.editables.user_profile import UserProfileEditables

if TYPE_CHECKING:
    from wies.core.inline_edit.base import EditableSet

REGISTRY: dict[str, type[EditableSet]] = {
    "assignment": AssignmentEditables,
    "colleague": ColleagueEditables,
    "placement": PlacementEditables,
    "service": ServiceEditables,
    "user": UserProfileEditables,
}

__all__ = [
    "REGISTRY",
    "AssignmentEditables",
    "ColleagueEditables",
    "PlacementEditables",
    "ServiceEditables",
    "UserProfileEditables",
]
