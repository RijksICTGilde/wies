"""All permission rules for the wies app.

Open this file to see who can do what — every ``@rule`` is a row in the
permission matrix. Engine: ``wies/core/permission_engine.py``.

Imported in ``wies.core.apps.CoreConfig.ready`` so registrations happen
at startup.
"""

from __future__ import annotations

from django.conf import settings

from wies.core.editables import (
    AssignmentEditables,
    ServiceEditables,
    UserEditables,
)
from wies.core.models import Assignment, Colleague, Placement, Service
from wies.core.permission_engine import Verb, has_permission, rule
from wies.rijksauth.models import User

UPDATE = Verb.UPDATE
DELETE = Verb.DELETE


# --- Private predicates ------------------------------------------------------


def _is_wies_sourced(assignment) -> bool:
    return assignment.source in ("wies", "")


def _has_change_perm(user, obj) -> bool:
    """True iff `user` holds the standard Django change_<model> permission for `obj`.

    Uses ``app_label`` so models in ``rijksauth`` (User) and ``core``
    (Assignment, Service, Placement, Colleague) both resolve correctly.
    """
    return user.has_perm(f"{obj._meta.app_label}.change_{obj._meta.model_name}")  # noqa: SLF001 — _meta is Django's canonical model-introspection API


def _is_assignment_owner(user, assignment) -> bool:
    colleague = getattr(user, "colleague", None)
    return bool(colleague and assignment.owner_id == colleague.id)


def _is_placed_on_assignment(user, assignment) -> bool:
    colleague = getattr(user, "colleague", None)
    if not colleague:
        return False
    return Placement.objects.filter(service__assignment=assignment, colleague=colleague).exists()


def _is_placed_on_service(user, service) -> bool:
    colleague = getattr(user, "colleague", None)
    if not colleague:
        return False
    return Placement.objects.filter(service=service, colleague=colleague).exists()


def _can_edit_assignment_text_field(user, assignment) -> bool:
    """BM-owner, Beheerder (``change_assignment``) or a placed
    consultant — but only on wies-sourced opdrachten."""
    if not _is_wies_sourced(assignment):
        return False
    return has_permission(UPDATE, assignment, user) or _is_placed_on_assignment(user, assignment)


def is_staff_member(user):
    """Whether the given user is a member of the support staff cohort (``STAFF_EMAILS``).

    Used both as a page-access gate (``/beheer/statistieken/``, ``/beheer/database/``)
    and as a per-row edit-permission predicate (e.g. in ``update_assignment``).
    """
    return user.is_authenticated and user.email.lower() in settings.STAFF_EMAILS


# --- Whole-object UPDATE rules ----------------------------------------------


@rule(UPDATE, Assignment)
def update_assignment(user, a):
    """Full edit: BM owner of a wies-sourced assignment, holder of
    core.change_assignment, or a support-staff member (``STAFF_EMAILS``).

    Placed colleagues do NOT pass — they get narrower access via the
    field-level rules for description/extra_info below.
    """
    if not _is_wies_sourced(a):
        return False
    return _has_change_perm(user, a) or _is_assignment_owner(user, a) or is_staff_member(user)


@rule(UPDATE, Service)
def update_service(user, s):
    """Service edits chain to the parent assignment."""
    return has_permission(UPDATE, s.assignment, user)


@rule(UPDATE, Placement)
def update_placement(user, p):
    """Reparenting team members is the assignment owner's call."""
    return has_permission(UPDATE, p.service.assignment, user)


@rule(UPDATE, Colleague)
def update_colleague(user, c):
    """Admin (Beheerder via has_perm), or the colleague themselves."""
    return _has_change_perm(user, c) or getattr(user, "colleague", None) == c


@rule(UPDATE, User)
def update_user(user, target):
    """Admin path (Beheerder holds rijksauth.change_user) or self-edit."""
    return _has_change_perm(user, target) or target == user


# --- Whole-object DELETE rules ----------------------------------------------


@rule(DELETE, Assignment)
def delete_assignment(user, a):
    """The BM-owner of a wies-sourced opdracht, or a support-staff
    member (``STAFF_EMAILS``) (issue #313).

    Beheerder (``core.change_assignment``) is intentionally NOT
    included here — deletion stays with the owner who has end-to-end
    accountability for the opdracht, plus staff for support cases.
    """
    return _is_wies_sourced(a) and (_is_assignment_owner(user, a) or is_staff_member(user))


# --- Field-level UPDATE rules -----------------------------------------------


@rule(UPDATE, AssignmentEditables.extra_info)
def update_assignment_extra_info(user, a):
    return _can_edit_assignment_text_field(user, a)


@rule(UPDATE, AssignmentEditables.name)
def update_assignment_name(user, a):
    return _can_edit_assignment_text_field(user, a)


@rule(UPDATE, ServiceEditables.description)
def update_service_description(user, s):
    """Assignment owner (BM) or the consultant placed on this specific service."""
    return _is_wies_sourced(s.assignment) and (
        has_permission(UPDATE, s.assignment, user) or _is_placed_on_service(user, s)
    )


@rule(UPDATE, UserEditables.email)
def update_user_email(user, target):
    """Email is admin-only — even on the user's own profile.

    Stricter than the whole-object User rule: no self-edit branch.
    """
    return _has_change_perm(user, target)
