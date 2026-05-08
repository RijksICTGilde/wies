"""Explicit model_label → EditableSet mapping for runtime dispatch."""

from typing import TYPE_CHECKING

from wies.core.editables.assignment import AssignmentEditables
from wies.core.editables.colleague import ColleagueEditables
from wies.core.editables.placement import PlacementEditables
from wies.core.editables.service import ServiceEditables
from wies.core.editables.user import UserEditables

if TYPE_CHECKING:
    from wies.core.inline_edit.base import EditableSet

REGISTRY: dict[str, type[EditableSet]] = {
    "assignment": AssignmentEditables,
    "colleague": ColleagueEditables,
    "placement": PlacementEditables,
    "service": ServiceEditables,
    "user": UserEditables,
}

__all__ = [
    "REGISTRY",
    "AssignmentEditables",
    "ColleagueEditables",
    "PlacementEditables",
    "ServiceEditables",
    "UserEditables",
]
