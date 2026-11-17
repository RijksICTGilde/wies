"""Staff pages: role matrix, dashboard, error log and database tools."""

import requests
from django.conf import settings
from django.contrib import messages
from django.core import management
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from wies.core.models import (
    Assignment,
    Colleague,
    ErrorEvent,
    Label,
    LabelCategory,
    OrganizationType,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
)
from wies.core.roles import (
    staff_required,
    user_admin_required,
)
from wies.core.services import role_matrix as role_matrix_rules
from wies.core.services.access_requests import ops_notification
from wies.core.services.events import create_event
from wies.core.services.mattermost import parse_channel_url, send_ops_message
from wies.core.services.tasks import create_task, get_latest_tasks, has_active_task
from wies.rijksauth.services.usage import get_usage_stats

from .panels import _merge_preview_rows


@user_admin_required
def role_matrix(request):
    return render(
        request,
        "role_matrix.html",
        {
            "columns": [heading for heading, _groups, _staff in role_matrix_rules.COLUMNS],
            "sections": role_matrix_rules.build_matrix(),
            "group_permissions": role_matrix_rules.group_permissions(),
            "may_assign_roles": request.user.has_perm("rijksauth.change_user"),
        },
    )


ERRORS_PER_PAGE = 10


@staff_required
def staff_dashboard(request):
    return render(
        request,
        "staff_dashboard.html",
        {"usage": get_usage_stats(), **_error_table_context(page_number=None)},
    )


def _error_table_context(page_number):
    """Context for the paginated error table (shared by the dashboard and the endpoint)."""
    paginator = Paginator(ErrorEvent.objects.select_related("user"), ERRORS_PER_PAGE)
    page_obj = paginator.get_page(page_number)

    def page_url(number):
        return f"{reverse('error-table')}?pagina={number}"

    return {
        "object_list": page_obj.object_list,
        "page_obj": page_obj,
        "previous_page_url": page_url(page_obj.previous_page_number()) if page_obj.has_previous() else None,
        "next_page_url": page_url(page_obj.next_page_number()) if page_obj.has_next() else None,
    }


def _render_error_table(request, page_number):
    """Render the paginated error table fragment for the given page."""
    return render(request, "parts/error_table.html", _error_table_context(page_number))


@staff_required
def error_table(request):
    """Paginated error table fragment, loaded via HTMX by the dashboard."""
    return _render_error_table(request, request.GET.get("pagina"))


@staff_required
def error_detail(request, public_id):

    error = get_object_or_404(ErrorEvent, public_id=public_id)
    return render(request, "error_detail.html", {"error": error})


@staff_required
def delete_error(request, public_id):
    """Confirms (GET → modal) and performs (POST) deletion of a single error."""
    error = get_object_or_404(ErrorEvent, public_id=public_id)
    if request.method == "GET":
        return render(
            request,
            "parts/confirm_delete_modal.html",
            {
                "dialog_text": "Foutmelding verwijderen?",
                "dialog_supporting": (
                    "Weet je zeker dat je deze foutmelding wilt verwijderen? "
                    "Verwijderen is permanent en niet terug te draaien."
                ),
                "confirm_label": "Verwijder foutmelding",
                "cancel_label": "Behoud foutmelding",
                "form_post_url": reverse("delete-error", kwargs={"public_id": public_id}),
            },
        )
    if request.method == "POST":
        error.delete()
        response = HttpResponse(status=200)
        response["HX-Redirect"] = reverse("staff-dashboard")
        return response
    return HttpResponse(status=405)


def _send_test_ops_notification(request) -> None:
    """Posts the real access request notification, so an environment's Mattermost
    settings can be checked without someone having to request access."""
    try:
        sent = send_ops_message(ops_notification(request))
    except requests.HTTPError as exc:
        messages.error(
            request,
            f"Mattermost weigerde de melding (fout {exc.response.status_code}). "
            "Controleer het token en of de bot lid is van het kanaal.",
        )
        return
    except requests.RequestException:
        messages.error(request, "Mattermost is niet bereikbaar. Probeer het later opnieuw.")
        return
    except ValueError:
        messages.error(request, "Het Mattermost-kanaal is geen geldige kanaallink. Controleer de instelling.")
        return
    if not sent:
        messages.error(request, "Mattermost is niet ingesteld: het token of het kanaal ontbreekt.")
        return
    _base_url, _team, channel = parse_channel_url(settings.MATTERMOST_WIES_OPS_CHANNEL_URL)
    messages.success(request, f"De melding is verstuurd naar het Mattermost-kanaal {channel}.")


@staff_required
def staff_database(request):
    context = {
        "assignment_count": Assignment.objects.count(),
        "colleague_count": Colleague.objects.count(),
        "organization_count": OrganizationUnit.objects.count(),
        "latest_tasks": get_latest_tasks(limit=3),
        "destructive_actions_enabled": settings.ENABLE_DESTRUCTIVE_STAFF_ACTIONS,
    }
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "clear_data":
            if not settings.ENABLE_DESTRUCTIVE_STAFF_ACTIONS:
                return HttpResponse(status=405)
            # not using flush, since that would clear users
            Assignment.objects.all().delete()
            Colleague.objects.all().delete()
            Skill.objects.all().delete()
            Placement.objects.all().delete()
            Service.objects.all().delete()
            LabelCategory.objects.all().delete()
            Label.objects.all().delete()
            OrganizationUnit.objects.update(parent=None)
            OrganizationUnit.objects.all().delete()
            OrganizationType.objects.all().delete()
        elif action == "load_base_data":
            if not settings.ENABLE_DESTRUCTIVE_STAFF_ACTIONS:
                return HttpResponse(status=405)
            # The generator clears the dummy data it owns first, so reseeding an
            # environment that already has data regenerates cleanly.
            management.call_command("load_dummy_data", profile="base")
            messages.success(request, "Dummy data gegenereerd")
        elif action == "test_ops_notification":
            _send_test_ops_notification(request)
        elif action == "reset_onboarding":
            request.user.onboarding_completed_at = None
            request.user.save(update_fields=["onboarding_completed_at"])
            # No message: the wizard reopens right after the redirect, and a
            # notification would fall behind it — the wizard is a modal in the
            # top layer, the notification region is not.
        elif action == "sync_organizations":
            # Check if there's already an active task
            if has_active_task("sync_organizations"):
                messages.error(request, "Er is al een sync_organizations taak actief. Wacht tot deze is afgerond.")
            else:
                # Create a new task
                create_task(
                    command="sync_organizations",
                    created_by=request.user,
                    timeout_minutes=5,
                )
                messages.success(request, "Organisatiesynchronisatie is gestart")

            # If this is an HTMX request, return partial HTML
            if request.headers.get("HX-Request"):
                context["latest_tasks"] = get_latest_tasks(limit=3)
                return render(request, "parts/task_list.html", context)

        elif action == "publish_startpage":
            # Publish the start page from the content repo — the db_worker runs
            # the startpage_publish task. Shares the same task list as the other actions.
            from wies.startpage.publish import (  # noqa: PLC0415 (import not at top level) — only this rare admin action needs it
                STARTPAGE_PUBLISH_COMMAND,
                STARTPAGE_PUBLISH_TIMEOUT_MINUTES,
            )

            if has_active_task(STARTPAGE_PUBLISH_COMMAND):
                messages.error(request, "Er is al een publicatietaak actief. Wacht tot deze is afgerond.")
            else:
                create_task(
                    command=STARTPAGE_PUBLISH_COMMAND,
                    created_by=request.user,
                    timeout_minutes=STARTPAGE_PUBLISH_TIMEOUT_MINUTES,
                )
                messages.success(request, "Publicatie is gestart")

            if request.headers.get("HX-Request"):
                context["latest_tasks"] = get_latest_tasks(limit=3)
                return render(request, "parts/task_list.html", context)

        elif action == "merge_duplicates_preview":
            from wies.core.services.assignments import find_duplicate_groups  # noqa: PLC0415

            groups = find_duplicate_groups()
            # The sheet opens even without duplicates: the empty case is handled
            # inside it. Rows are flat (one per placement) because a reviewer
            # reads per line, so the overview needs no nested loops.
            context["merge_groups"] = [
                {
                    "name": group[0].name,
                    "owner": str(group[0].owner),
                    "count": len(group),
                    "target_id": group[0].id,
                    "rows": _merge_preview_rows(group),
                }
                for group in groups
            ]
            return render(request, "parts/merge_duplicates_sheet.html", context)

        elif action == "merge_duplicates_apply":
            # Deliberately not behind ENABLE_DESTRUCTIVE_STAFF_ACTIONS:
            # this merge is a cleanup meant for production data.
            from wies.core.services.assignments import (  # noqa: PLC0415 — conditional import for rare admin action
                find_duplicate_groups,
                merge_group,
            )

            groups = find_duplicate_groups()
            if not groups:
                messages.info(request, "Geen dubbele opdrachten gevonden.")
            else:
                with transaction.atomic():
                    # Both numbers count assignments, in the same wording as the
                    # sheet that was just confirmed; "in 2 groep(en)" left it
                    # unclear whether groups or assignments were meant.
                    samengevoegd = sum(len(g) for g in groups)
                    overgebleven = len(groups)
                    for group in groups:
                        target = group[0]
                        deleted_ids = [a.id for a in group[1:]]
                        merge_group(group)
                        create_event(
                            object_type="Assignment",
                            action="update",
                            source="user",
                            object_id=target.id,
                            user=request.user,
                            request=request,
                            context={
                                "merge": True,
                                "merged_ids": deleted_ids,
                                "name": target.name,
                            },
                        )
                    messages.success(
                        request,
                        f"{samengevoegd} opdrachten samengevoegd tot {overgebleven} "
                        f"{'opdracht' if overgebleven == 1 else 'opdrachten'}.",
                    )

        return redirect("staff-database")

    return render(request, "staff_database.html", context)
