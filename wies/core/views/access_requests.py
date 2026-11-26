"""Access requests: the sheet on the no-access page and the beheer page that decides."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_not_required, permission_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from wies.core.forms import AccessRequestApproveForm, AccessRequestForm, AccessRequestRejectForm
from wies.core.models import AccessRequest, ContractPeriod
from wies.core.permission_engine import Verb, has_permission
from wies.core.roles import role_required
from wies.core.services import access_requests
from wies.core.services.dates import datum_nl, local_date
from wies.core.services.users import is_allowed_email_domain
from wies.rijksauth.views import FAILED_LOGIN_CLAIMS_SESSION_KEY

from ._common import hx_redirect
from .users import access_decision_message, create_user_with_contract_period

# Set for one page view after a request was stored, so the page says it was sent.
ACCESS_REQUEST_SENT_SESSION_KEY = "access_request_sent"


def access_request_state(request) -> access_requests.AccessRequestState | None:
    """What the no-access page offers this login, or None when it offers no request.

    Read, not popped: the request sheet posts back to the same session. Logging out
    flushes it.
    """
    if request.user.is_authenticated:
        return None
    claims = request.session.get(FAILED_LOGIN_CLAIMS_SESSION_KEY)
    if not claims or not is_allowed_email_domain(claims["email"]):
        return None
    return access_requests.state_for_claims(claims)


def _back_to_no_access(request) -> HttpResponse:
    if "HX-Request" in request.headers:
        return hx_redirect(settings.AUTH_NO_ACCESS_URL)
    return redirect(settings.AUTH_NO_ACCESS_URL)


@login_not_required  # for a login that found no account; the session claims are the gate
def access_request_create(request):
    """The request sheet: GET returns it, POST stores the request.

    Only for a verified login without an account and without a pending request;
    anything else goes back to the page that explains why.
    """
    access = access_request_state(request)
    if access is None or not access.may_request:
        return _back_to_no_access(request)
    claims = request.session[FAILED_LOGIN_CLAIMS_SESSION_KEY]

    if request.method == "POST":
        form = AccessRequestForm(request.POST)
        if form.is_valid():
            if access_requests.submit_access_request(claims, form.cleaned_data, request=request):
                request.session[ACCESS_REQUEST_SENT_SESSION_KEY] = True
            return _back_to_no_access(request)
    else:
        form = AccessRequestForm(initial={"first_name": claims["given_name"], "last_name": claims["family_name"]})
    return render(
        request,
        "parts/access_request_sheet.html",
        {"content": form, "email": claims["email"], "form_post_url": reverse("access-request-create")},
    )


def _may_decide_access_requests(user) -> bool:
    return has_permission(Verb.UPDATE, AccessRequest(), user)


access_request_admin_required = role_required(_may_decide_access_requests)


def day_text(moment) -> str:
    return datum_nl(local_date(moment), "j b")


# Both decisions open in the mount the user sheet uses.
_OPENS_IN_MODAL = {"hx-target": "#userFormModal", "hx-swap": "innerHTML"}


def _pending_row(access_request) -> dict:
    suborganization = access_request.suborganization
    details = [
        access_request.email,
        suborganization.name if suborganization else "Geen onderdeel",
        f"aangevraagd {day_text(access_request.created_at)}",
    ]
    if access_request.motivation:
        details.append(f"“{access_request.motivation}”")
    approve_url = reverse("access-request-approve", args=[access_request.public_id])
    reject_url = reverse("access-request-reject", args=[access_request.public_id])
    return {
        "name": access_request.full_name,
        "details": " · ".join(details),
        "actions": [
            {"text": "Goedkeuren", "attrs": {"hx-get": approve_url, **_OPENS_IN_MODAL}},
            {"text": "E-mailen", "attrs": {"href": f"mailto:{access_request.email}"}},
            {"text": "Afwijzen", "attrs": {"destructive": "", "hx-get": reject_url, **_OPENS_IN_MODAL}},
        ],
    }


def _decided_row(request, access_request) -> dict:
    approved = access_request.status == AccessRequest.Status.APPROVED
    decider = access_request.decided_by.get_full_name() if access_request.decided_by else "een verwijderde gebruiker"
    details = [access_request.email, f"door {decider} op {day_text(access_request.decided_at)}"]
    if access_request.decision_note:
        details.append(f"Reden: {access_request.decision_note}")
    actions = []
    # Without a relay the beheerder sends the approval mail from their own mail program.
    if approved and not settings.EMAIL_ENABLED:
        mailto = access_requests.approval_mailto(access_request, request)
        actions.append({"text": "E-mailen dat er toegang is", "icon": "envelope", "attrs": {"href": mailto}})
    return {
        "name": access_request.full_name,
        "details": " · ".join(details),
        "status_label": access_request.get_status_display(),
        "approved": approved,
        "actions": actions,
    }


def _decision_form(form_class, request, mail_label: str, **kwargs):
    """The approve or reject form; the mail checkbox only when Wies can send mail."""
    form = form_class(request.POST if request.method == "POST" else None, **kwargs)
    if settings.EMAIL_ENABLED:
        form.fields["send_mail"].label = mail_label
    else:
        del form.fields["send_mail"]
    return form


@access_request_admin_required
def access_request_admin(request):
    access_requests.purge_decided()
    pending = AccessRequest.objects.filter(status=AccessRequest.Status.PENDING).select_related("suborganization")
    decided = (
        AccessRequest.objects.exclude(status=AccessRequest.Status.PENDING)
        .select_related("decided_by", "created_user")
        .order_by("-decided_at")
    )
    return render(
        request,
        "access_request_admin.html",
        {
            "pending": [_pending_row(access_request) for access_request in pending],
            "decided": [_decided_row(request, access_request) for access_request in decided],
            "retention_days": access_requests.DECIDED_RETENTION.days,
        },
    )


def _back_to_access_request_admin() -> HttpResponse:
    return hx_redirect(reverse("access-request-admin"))


def _pending_access_request_or_back(request, public_id):
    """``(request, None)`` while pending; ``(None, response)`` once decided.

    Two beheerders get the same notification: the second one's click must say what
    happened, and htmx shows nothing for a 404.
    """
    access_request = get_object_or_404(AccessRequest, public_id=public_id)
    if access_request.status == AccessRequest.Status.PENDING:
        return access_request, None
    return None, _already_decided(request, access_request)


def _already_decided(request, access_request) -> HttpResponse:
    messages.info(request, f"De toegangsaanvraag van {access_request.full_name} is al afgehandeld.")
    return _back_to_access_request_admin()


@access_request_admin_required
@permission_required("rijksauth.add_user", raise_exception=True)
def access_request_approve(request, public_id):
    """Approving is creating the user: the user sheet, prefilled, with the address
    locked to the one the request came from. ``create_user`` closes the request."""
    access_request, decided = _pending_access_request_or_back(request, public_id)
    if decided:
        return decided
    # Same gate as user_create: the sheet carries the first contract period.
    if not has_permission(Verb.UPDATE, ContractPeriod(), request.user):
        return HttpResponseForbidden()
    initial = {
        "first_name": access_request.first_name,
        "last_name": access_request.last_name,
        "email": access_request.email,
        "suborganization": access_request.suborganization,
    }
    form = _decision_form(
        AccessRequestApproveForm,
        request,
        f"Stuur {access_request.first_name} een e-mail dat er toegang is",
        initial=initial,
        editor=request.user,
    )
    # Disabled: Django takes the initial value and ignores whatever is posted.
    form.fields["email"].disabled = True
    if request.method == "POST" and form.is_valid():
        mailed = form.cleaned_data.get("send_mail", False)
        if user := create_user_with_contract_period(request, form, mail_access_request=mailed):
            text = f"{user.first_name} {user.last_name} heeft nu toegang tot Wies."
            access_decision_message(request, text, user.first_name, mailed=mailed)
            return _back_to_access_request_admin()
    return render(
        request,
        "parts/user_form_modal.html",
        {
            "content": form,
            "form_post_url": reverse("access-request-approve", args=[access_request.public_id]),
            "modal_title": "Toegangsaanvraag goedkeuren",
            "form_button_label": "Voeg gebruiker toe",
            "modal_element_id": "userFormModal",
            "target_element_id": "userFormModal",
        },
    )


@access_request_admin_required
def access_request_reject(request, public_id):
    access_request, decided = _pending_access_request_or_back(request, public_id)
    if decided:
        return decided
    form = _decision_form(
        AccessRequestRejectForm, request, f"Stuur {access_request.first_name} een e-mail met de afwijzing"
    )
    if request.method == "POST" and form.is_valid():
        mailed = form.cleaned_data.get("send_mail", False)
        if not access_requests.reject(
            access_request, request.user, form.cleaned_data["decision_note"], request=request, send_mail=mailed
        ):
            return _already_decided(request, access_request)
        access_decision_message(
            request,
            f"De toegangsaanvraag van {access_request.full_name} is afgewezen.",
            access_request.first_name,
            mailed=mailed,
        )
        return _back_to_access_request_admin()
    return render(
        request,
        "parts/access_request_reject_modal.html",
        {
            "content": form,
            "access_request": access_request,
            "form_post_url": reverse("access-request-reject", args=[access_request.public_id]),
        },
    )
