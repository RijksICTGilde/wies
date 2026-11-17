"""Access requests: someone without an account asks for one, a Gebruikersbeheerder decides."""

import logging
import smtplib
from dataclasses import dataclass
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from wies.core.models import AccessRequest
from wies.core.services.events import create_event
from wies.core.services.mattermost import send_ops_message

User = get_user_model()

logger = logging.getLogger(__name__)

# After a rejection the same address may not ask again for this long.
REJECTION_COOLDOWN = timedelta(days=30)
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
    if latest.decided_at and timezone.now() - latest.decided_at < REJECTION_COOLDOWN:
        return AccessRequestState(AccessState.REJECTED, latest)
    return AccessRequestState(AccessState.FORM)


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


def site_url(path: str, request=None) -> str:
    """An absolute link for outside Wies (chat, mail)."""
    if settings.SITE_BASE_URL or request is None:
        return f"{settings.SITE_BASE_URL}{path}"
    return request.build_absolute_uri(path)


def approval_mail(access_request: AccessRequest, request=None) -> tuple[str, str]:
    """Subject and body of the mail that says the account is there."""
    body = (
        f"Hoi {access_request.first_name},\n\n"
        f"Je hebt nu toegang tot Wies. Log in via {site_url(reverse('login'), request)}\n\n"
        "Heb je een vraag? Antwoord dan op deze e-mail.\n\n"
        "Groet,\nTeam Wies"
    )
    return "Je hebt toegang tot Wies", body


def _rejection_mail(access_request: AccessRequest) -> tuple[str, str]:
    reason = f"De reden: {access_request.decision_note}\n\n" if access_request.decision_note else ""
    body = (
        f"Hoi {access_request.first_name},\n\n"
        "Een gebruikersbeheerder heeft je toegangsaanvraag voor Wies afgewezen.\n\n"
        f"{reason}"
        f"Over {REJECTION_COOLDOWN.days} dagen kun je opnieuw toegang aanvragen. "
        "Heb je een vraag? Antwoord dan op deze e-mail.\n\n"
        "Groet,\nTeam Wies"
    )
    return "Je toegangsaanvraag voor Wies is afgewezen", body


def _mail_after_commit(access_request: AccessRequest, subject: str, body: str) -> None:
    """Sent once the decision is stored; a relay that fails costs a warning, not the decision."""
    if not settings.EMAIL_ENABLED:
        return
    message = EmailMessage(subject, body, to=[access_request.email], reply_to=[settings.EMAIL_REPLY_TO])

    def send() -> None:
        try:
            message.send()
        except smtplib.SMTPException, OSError:
            logger.warning("Could not mail the access request decision", exc_info=True)

    transaction.on_commit(send)


def ops_notification(request=None) -> str:
    """What the ops channel gets for a new request. No name or address: the
    channel is wider than the Gebruikersbeheerders."""
    return f"Nieuwe toegangsaanvraag voor Wies: {site_url(reverse('access-request-admin'), request)}"


def _notify_ops(request) -> None:
    """Tells the ops channel there is something to decide."""
    try:
        send_ops_message(ops_notification(request))
    except requests.RequestException, ValueError:
        # The request is stored; the counter in the app still shows it. ValueError:
        # a malformed channel URL, which must not cost the requester a 500.
        logger.warning("Could not post the access request notification to Mattermost", exc_info=True)


def _decide(access_request: AccessRequest, status: str, decided_by, request, **fields) -> None:
    access_request.status = status
    access_request.decided_at = timezone.now()
    access_request.decided_by = decided_by
    for name, value in fields.items():
        setattr(access_request, name, value)
    access_request.save()
    create_event(
        object_type="AccessRequest",
        action="update",
        source="user",
        object_id=access_request.id,
        user=decided_by,
        request=request,
        context={"status": status, "decision_note": access_request.decision_note},
    )


def approve(access_request: AccessRequest, created_user, decided_by, request=None, *, send_mail: bool = True) -> None:
    _decide(access_request, AccessRequest.Status.APPROVED, decided_by, request, created_user=created_user)
    if send_mail:
        _mail_after_commit(access_request, *approval_mail(access_request, request))


def reject(access_request: AccessRequest, decided_by, note: str = "", request=None, *, send_mail: bool = True) -> None:
    _decide(access_request, AccessRequest.Status.REJECTED, decided_by, request, decision_note=note)
    if send_mail:
        _mail_after_commit(access_request, *_rejection_mail(access_request))


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
