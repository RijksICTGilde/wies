"""Access requests: the sheet on the no-access page and the beheer page that decides."""

import urllib.parse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_not_required, permission_required, user_passes_test
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from wies.core.forms import AccessRequestForm, AccessRequestRejectForm, UserForm
from wies.core.models import AccessRequest, ContractPeriod
from wies.core.permission_engine import Verb, has_permission
from wies.core.services import access_requests
from wies.core.services.users import is_allowed_email_domain
from wies.rijksauth.views import FAILED_LOGIN_CLAIMS_SESSION_KEY

from .users import _create_user_with_contract_period

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
        response = HttpResponse(status=200)
        response["HX-Redirect"] = settings.AUTH_NO_ACCESS_URL
        return response
    return redirect(settings.AUTH_NO_ACCESS_URL)


@login_not_required  # for a login that found no account; the session claims are the gate
def access_request_create(request):
    """The request sheet: GET returns it, POST stores the request.

    Only for a verified login without an account and without a pending or recently
    rejected request; anything else goes back to the page that explains why.
    """
    access = access_request_state(request)
    if access is None or access.kind != access_requests.AccessState.FORM:
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


def access_request_admin_required(view_func):
    """Logged in but not allowed: the no-access page. Not logged in: the login.

    LoginRequiredMiddleware sends an anonymous visitor to the view's own
    ``login_url``, so the one user_passes_test sets has to be put back.
    """
    wrapped = user_passes_test(_may_decide_access_requests, login_url="/geen-toegang/")(view_func)
    wrapped.login_url = settings.LOGIN_URL
    return wrapped


def _approved_mailto(request, access_request) -> str:
    """A prepared mail for the beheerder: Wies sends no mail itself (yet)."""
    login_path = reverse("login")
    login_url = (
        f"{settings.SITE_BASE_URL}{login_path}" if settings.SITE_BASE_URL else request.build_absolute_uri(login_path)
    )
    query = urllib.parse.urlencode(
        {
            "subject": "Je hebt toegang tot Wies",
            "body": f"Hoi {access_request.first_name},\n\nJe hebt nu toegang tot Wies. Log in via {login_url}",
        },
        quote_via=urllib.parse.quote,
    )
    return f"mailto:{access_request.email}?{query}"


@access_request_admin_required
def access_request_admin(request):
    access_requests.purge_decided()
    decided = list(
        AccessRequest.objects.exclude(status=AccessRequest.Status.PENDING)
        .select_related("decided_by")
        .order_by("-decided_at")
    )
    for access_request in decided:
        if access_request.status == AccessRequest.Status.APPROVED:
            access_request.mailto = _approved_mailto(request, access_request)
    return render(
        request,
        "access_request_admin.html",
        {
            "pending": AccessRequest.objects.filter(status=AccessRequest.Status.PENDING).select_related(
                "suborganization"
            ),
            "decided": decided,
            "retention_days": access_requests.DECIDED_RETENTION.days,
        },
    )


def _back_to_access_request_admin() -> HttpResponse:
    response = HttpResponse(status=200)
    response["HX-Redirect"] = reverse("access-request-admin")
    return response


def _pending_access_request_or_back(request, public_id):
    """``(request, None)`` while pending; ``(None, response)`` once decided.

    Two beheerders get the same notification: the second one's click must say what
    happened, and htmx shows nothing for a 404.
    """
    access_request = get_object_or_404(AccessRequest, public_id=public_id)
    if access_request.status == AccessRequest.Status.PENDING:
        return access_request, None
    messages.info(request, f"De toegangsaanvraag van {access_request.full_name} is al afgehandeld.")
    return None, _back_to_access_request_admin()


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
    form = UserForm(request.POST if request.method == "POST" else None, initial=initial, editor=request.user)
    # Disabled: Django takes the initial value and ignores whatever is posted.
    form.fields["email"].disabled = True
    if request.method == "POST" and form.is_valid() and _create_user_with_contract_period(request, form):
        messages.success(request, f"{access_request.full_name} heeft nu toegang tot Wies.")
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
    form = AccessRequestRejectForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        access_requests.reject(access_request, request.user, form.cleaned_data["decision_note"], request=request)
        messages.success(request, f"De toegangsaanvraag van {access_request.full_name} is afgewezen.")
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
