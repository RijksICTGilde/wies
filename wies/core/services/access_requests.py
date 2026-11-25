"""Access requests: someone without an account asks for one, a Gebruikersbeheerder decides."""

import logging
import smtplib
from dataclasses import dataclass
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from wies.core.models import AccessRequest
from wies.core.services.events import create_event
from wies.core.services.mattermost import send_ops_message
from wies.core.services.urls import site_url

User = get_user_model()

logger = logging.getLogger(__name__)

# Decided requests hold a name and free text of someone who may never get an
# account (docs/privacy.md); the audit event outlives them.
DECIDED_RETENTION = timedelta(days=90)


class AccessState:
    FORM = "form"
    PENDING = "pending"
    REJECTED = "rejected"
    ACCOUNT_EXISTS = "account_exists"


@dataclass(frozen=True)
class AccessRequestState:
    kind: str
    access_request: AccessRequest | None = None

    @property
    def may_request(self) -> bool:
        """A rejection does not block a new request; the page shows it above the button."""
        return self.kind in (AccessState.FORM, AccessState.REJECTED)


def state_for_claims(claims: dict | None) -> AccessRequestState | None:
    """What the no-access page offers this login; None when it offers no request at all.

    No claims means an unverified address or an expired session. The caller has
    already turned away another domain.
    """
    if not claims:
        return None
    email = claims["email"]
    # The backend claims an unbound account on login, so an account found here is
    # bound to another subject: a request could never become this person's account.
    if User.objects.filter(email__iexact=email).exists():
        return AccessRequestState(AccessState.ACCOUNT_EXISTS)
    latest = AccessRequest.objects.filter(email__iexact=email).order_by("-created_at").first()
    if latest is None or latest.status == AccessRequest.Status.APPROVED:
        return AccessRequestState(AccessState.FORM)
    if latest.status == AccessRequest.Status.PENDING:
        return AccessRequestState(AccessState.PENDING, latest)
    return AccessRequestState(AccessState.REJECTED, latest)


def submit_access_request(claims: dict, cleaned_data: dict, request=None) -> AccessRequest | None:
    """Stores the request for the address in ``claims``; None when one is already pending."""
    try:
        with transaction.atomic():
            access_request = AccessRequest.objects.create(
                email=claims["email"],
                first_name=cleaned_data["first_name"],
                last_name=cleaned_data["last_name"],
                suborganization=cleaned_data.get("suborganization"),
                motivation=cleaned_data.get("motivation", ""),
            )
    except IntegrityError:
        return None
    # The requester has no account, so the event carries the address instead of
    # a user; the motivation stays out of the audit trail.
    create_event(
        object_type="AccessRequest",
        action="create",
        source="user",
        object_id=access_request.id,
        request=request,
        context={"email": access_request.email},
    )
    _notify_ops(request)
    return access_request


def approval_mail(first_name: str, request=None) -> tuple[str, str]:
    """Subject and body of the mail that says the account is there."""
    body = (
        f"Hoi {first_name},\n\n"
        f"Je hebt nu toegang tot Wies. Log in via {site_url(reverse('login'), request)}\n\n"
        "Heb je een vraag? Antwoord dan op deze e-mail.\n\n"
        "Groet,\nTeam Wies"
    )
    return "Je hebt toegang tot Wies", body


def _rejection_mail(access_request: AccessRequest, request=None) -> tuple[str, str]:
    reason = f"De reden: {access_request.decision_note}\n\n" if access_request.decision_note else ""
    body = (
        f"Hoi {access_request.first_name},\n\n"
        "Een gebruikersbeheerder heeft je toegangsaanvraag voor Wies afgewezen.\n\n"
        f"{reason}"
        f"Je kunt opnieuw toegang aanvragen via {site_url(reverse('login'), request)}\n\n"
        "Heb je een vraag? Antwoord dan op deze e-mail.\n\n"
        "Groet,\nTeam Wies"
    )
    return "Je toegangsaanvraag voor Wies is afgewezen", body


def _mail_after_commit(access_request: AccessRequest, subject: str, body: str, request=None) -> None:
    """Sent once the decision is stored; a relay that fails costs the mail, not the decision.

    The failure is marked on ``request`` for the beheerder's message (see
    ``decision_message``). The commit comes before that message: reject runs outside a
    transaction, approve at the end of the user's.
    """
    if not settings.EMAIL_ENABLED:
        return
    message = EmailMessage(subject, body, to=[access_request.email], reply_to=[settings.EMAIL_REPLY_TO])

    def send() -> None:
        try:
            message.send()
        except (smtplib.SMTPException, OSError) as exc:
            # TRY400 (logging.exception in except) suppressed: no traceback, as
            # SMTPRecipientsRefused carries the requester's address; only the type is logged.
            logger.error("Could not mail the access request decision: %s", type(exc).__name__)  # noqa: TRY400
            if request is not None:
                request.access_request_mail_failed = True

    transaction.on_commit(send)


def decision_message(request, text: str, first_name: str, *, mailed: bool) -> None:
    """The beheerder's message after a decision, saying whether the mail went out."""
    if not mailed:
        messages.success(request, text)
    elif getattr(request, "access_request_mail_failed", False):
        failed = f"De e-mail aan {first_name} kon niet worden verstuurd. Laat het {first_name} zelf weten."
        messages.warning(request, f"{text} {failed}")
    else:
        messages.success(request, f"{text} {first_name} krijgt hierover een e-mail.")


def _notify_ops(request) -> None:
    """Tells the ops channel there is something to decide. No name or address: the
    channel is wider than the Gebruikersbeheerders."""
    try:
        send_ops_message(f"Nieuwe toegangsaanvraag voor Wies: {site_url(reverse('access-request-admin'), request)}")
    except requests.RequestException, ValueError:
        # The request is stored; the counter in the app still shows it. ValueError:
        # a malformed channel URL, which must not cost the requester a 500.
        logger.warning("Could not post the access request notification to Mattermost", exc_info=True)


def _decide(access_request: AccessRequest, status: str, decided_by, request, **fields) -> bool:
    """Stores the decision; False when another beheerder decided first."""
    fields |= {"status": status, "decided_at": timezone.now(), "decided_by": decided_by}
    # On the pending row only: two beheerders deciding at once would otherwise
    # overwrite each other, and the second one's mail contradicts the first.
    pending = AccessRequest.objects.filter(pk=access_request.pk, status=AccessRequest.Status.PENDING)
    if not pending.update(**fields):
        return False
    for name, value in fields.items():
        setattr(access_request, name, value)
    create_event(
        object_type="AccessRequest",
        action="update",
        source="user",
        object_id=access_request.id,
        user=decided_by,
        request=request,
        # No decision_note: free text about someone, kept on the request for its retention only.
        context={"status": status},
    )
    return True


def approve(access_request: AccessRequest, created_user, decided_by, request=None, *, send_mail: bool = True) -> None:
    decided = _decide(access_request, AccessRequest.Status.APPROVED, decided_by, request, created_user=created_user)
    if decided and send_mail:
        # The name the beheerder confirmed on the user sheet, not the one typed in the request.
        _mail_after_commit(access_request, *approval_mail(created_user.first_name, request), request)


def reject(access_request: AccessRequest, decided_by, note: str = "", request=None, *, send_mail: bool = True) -> bool:
    """False when another beheerder decided first."""
    if not _decide(access_request, AccessRequest.Status.REJECTED, decided_by, request, decision_note=note):
        return False
    if send_mail:
        _mail_after_commit(access_request, *_rejection_mail(access_request, request), request)
    return True


def close_pending_for(user, decided_by, request=None, *, send_mail: bool = True) -> None:
    """A user created by hand (sheet or CSV) answers a pending request on their address."""
    pending = AccessRequest.objects.filter(email__iexact=user.email, status=AccessRequest.Status.PENDING).first()
    if pending is not None:
        approve(pending, user, decided_by, request, send_mail=send_mail)


def purge_decided() -> None:
    """Drops decided requests past their retention. Run lazily from the admin page:
    there is no scheduler, and that page is where they would be seen."""
    AccessRequest.objects.filter(decided_at__lt=timezone.now() - DECIDED_RETENTION).delete()


def pending_count(request) -> int:
    """Counted once per request: the sidebar and the user list both show it."""
    if not hasattr(request, "pending_access_request_count"):
        request.pending_access_request_count = AccessRequest.objects.filter(status=AccessRequest.Status.PENDING).count()
    return request.pending_access_request_count
