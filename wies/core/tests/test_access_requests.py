"""Access requests: someone without an account asks for one on /geen-toegang/,
a Gebruikersbeheerder approves or rejects it on /beheer/toegangsaanvragen/."""

import re
import smtplib
from datetime import timedelta
from unittest.mock import patch

import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.messages import get_messages
from django.core import mail
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from wies.core.models import AccessRequest, Colleague, Event, Suborganization
from wies.core.roles import ROLE_BUSINESS_MANAGER, ROLE_CONSULTANT, ROLE_USER_ADMIN, setup_roles
from wies.core.services.access_requests import DECIDED_RETENTION, approve, reject
from wies.core.services.users import create_user, create_users_from_csv
from wies.core.tests.role_helpers import (
    STAFF_EMAIL,
    grant_business_manager,
    grant_consultant,
    make_staff_user,
)

User = get_user_model()

NO_ACCESS_URL = "/geen-toegang/"
CREATE_URL = "/geen-toegang/aanvragen/"
ADMIN_URL = "/beheer/toegangsaanvragen/"
REQUESTER_EMAIL = "nieuw@rijksoverheid.nl"
# What the checked nldd-checkbox-field posts.
SEND_MAIL = {"send_mail": "on"}
SHEET_BUTTON = 'text="Vraag toegang aan"'
ALLOWED_DOMAINS = ["@rijksoverheid.nl", "@minbzk.nl"]


def make_user_admin(email="beheerder@rijksoverheid.nl", first_name="Gea", last_name="Beheer"):
    user = User.objects.create_user(email=email, first_name=first_name, last_name=last_name)
    Colleague.objects.create(name=f"{first_name} {last_name}", email=email, source="wies", user=user)
    user.groups.add(Group.objects.get(name=ROLE_USER_ADMIN))
    return user


def make_pending(email=REQUESTER_EMAIL, **fields) -> AccessRequest:
    defaults = {"first_name": "Nora", "last_name": "Nieuw"}
    return AccessRequest.objects.create(email=email, **(defaults | fields))


@override_settings(ALLOWED_EMAIL_DOMAINS=ALLOWED_DOMAINS, STAFF_EMAILS=[])
class RequesterTest(TestCase):
    """The anonymous visitor whose login found no account."""

    def setUp(self):
        patcher = patch("wies.core.services.access_requests.send_ops_message")
        self.send_ops_message = patcher.start()
        self.addCleanup(patcher.stop)

    def _login_without_account(self, email=REQUESTER_EMAIL, *, verified=True):
        """The session the OIDC callback leaves behind (wies/rijksauth/views.py)."""
        session = self.client.session
        session["failed_login_email"] = email
        if verified:
            session["failed_login_claims"] = {"email": email.lower(), "given_name": "Nora", "family_name": "Nieuw"}
        session.save()

    def _post(self, **data):
        return self.client.post(CREATE_URL, {"first_name": "Nora", "last_name": "Nieuw", **data})

    def test_sheet_button_shows_for_verified_login_on_allowed_domain(self):
        self._login_without_account()

        response = self.client.get(NO_ACCESS_URL)

        self.assertContains(response, SHEET_BUTTON)
        self.assertContains(response, CREATE_URL)

    def test_sheet_button_hidden_for_other_domain(self):
        self._login_without_account("iemand@gmail.com")

        response = self.client.get(NO_ACCESS_URL)

        self.assertNotContains(response, SHEET_BUTTON)
        self.assertContains(response, "ODI / BZK e-mailadres")
        assert self.client.get(CREATE_URL).status_code == 302

    def test_sheet_button_hidden_without_claims(self):
        self._login_without_account(verified=False)

        response = self.client.get(NO_ACCESS_URL)

        self.assertNotContains(response, SHEET_BUTTON)
        assert self.client.get(CREATE_URL)["Location"] == NO_ACCESS_URL

    def test_sheet_button_hidden_when_account_exists(self):
        User.objects.create_user(email="Nieuw@Rijksoverheid.nl")
        self._login_without_account()

        response = self.client.get(NO_ACCESS_URL)

        self.assertNotContains(response, SHEET_BUTTON)
        self.assertContains(response, "Er bestaat al een account")
        assert self.client.get(CREATE_URL)["Location"] == NO_ACCESS_URL

    def test_get_returns_sheet_prefilled_from_claims(self):
        self._login_without_account()

        response = self.client.get(CREATE_URL)

        assert response.status_code == 200
        self.assertContains(response, f"voor <strong>{REQUESTER_EMAIL}</strong>")
        self.assertContains(response, 'value="Nora"')
        self.assertContains(response, 'value="Nieuw"')

    def test_logged_in_user_cannot_open_sheet(self):
        self._login_without_account()
        self.client.force_login(User.objects.create_user(email="ingelogd@rijksoverheid.nl"))

        assert self.client.get(CREATE_URL)["Location"] == NO_ACCESS_URL
        assert self._post().status_code == 302
        assert not AccessRequest.objects.exists()

    def test_post_creates_one_request_for_the_session_address(self):
        suborganization = Suborganization.objects.create(name="Onderdeel A")
        self._login_without_account()

        response = self._post(
            email="ander@rijksoverheid.nl",
            suborganization=suborganization.public_id,
            motivation="Ik werk in team X.",
        )

        assert response.status_code == 302
        assert response["Location"] == NO_ACCESS_URL
        access_request = AccessRequest.objects.get()
        assert access_request.email == REQUESTER_EMAIL
        assert access_request.status == AccessRequest.Status.PENDING
        assert access_request.suborganization == suborganization
        assert access_request.motivation == "Ik werk in team X."

    def test_htmx_post_redirects_with_header(self):
        self._login_without_account()

        response = self.client.post(
            CREATE_URL, {"first_name": "Nora", "last_name": "Nieuw"}, headers={"HX-Request": "true"}
        )

        assert response.status_code == 200
        assert response["HX-Redirect"] == NO_ACCESS_URL
        assert AccessRequest.objects.count() == 1

    def test_second_post_creates_no_second_request(self):
        self._login_without_account()
        self._post()
        self.client.get(NO_ACCESS_URL)

        response = self._post(first_name="Anders")

        assert response["Location"] == NO_ACCESS_URL
        assert AccessRequest.objects.count() == 1
        assert AccessRequest.objects.get().first_name == "Nora"
        self.assertContains(self.client.get(NO_ACCESS_URL), "wacht nog op beoordeling")

    def test_sent_banner_shows_once_then_waiting_state(self):
        self._login_without_account()
        self._post()

        first = self.client.get(NO_ACCESS_URL)
        second = self.client.get(NO_ACCESS_URL)

        self.assertContains(first, "Je aanvraag is verstuurd")
        self.assertNotContains(first, "wacht nog op beoordeling")
        self.assertNotContains(second, "Je aanvraag is verstuurd")
        self.assertContains(second, "wacht nog op beoordeling")
        self.assertNotContains(second, SHEET_BUTTON)

    def test_rejected_page_shows_the_reason_and_offers_a_new_request(self):
        make_pending(
            status=AccessRequest.Status.REJECTED, decided_at=timezone.now(), decision_note="Geen ODI-medewerker"
        )
        self._login_without_account()

        page = self.client.get(NO_ACCESS_URL)

        self.assertContains(page, "Je aanvraag is afgewezen")
        self.assertContains(page, "Geen ODI-medewerker")
        self.assertContains(page, 'text="Vraag opnieuw toegang aan"')

    def test_post_allowed_right_after_rejection(self):
        make_pending(status=AccessRequest.Status.REJECTED, decided_at=timezone.now())
        self._login_without_account()

        self._post()

        assert AccessRequest.objects.filter(status=AccessRequest.Status.PENDING).count() == 1
        assert AccessRequest.objects.count() == 2
        self.assertContains(self.client.get(NO_ACCESS_URL), "Je aanvraag is verstuurd")

    def test_motivation_over_500_characters_is_a_form_error(self):
        self._login_without_account()

        response = self._post(motivation="x" * 501)

        assert response.status_code == 200
        self.assertContains(response, "500 tekens")
        assert not AccessRequest.objects.exists()

    def test_motivation_of_500_characters_is_accepted(self):
        self._login_without_account()

        self._post(motivation="x" * 500)

        assert AccessRequest.objects.count() == 1

    def test_missing_name_is_a_form_error(self):
        self._login_without_account()

        response = self.client.post(CREATE_URL, {"first_name": "", "last_name": "Nieuw"})

        assert response.status_code == 200
        self.assertContains(response, "Dit veld is verplicht")
        assert not AccessRequest.objects.exists()

    def test_event_logged_without_motivation(self):
        self._login_without_account()

        self._post(motivation="Geheime toelichting")

        access_request = AccessRequest.objects.get()
        event = Event.objects.get(object_type="AccessRequest")
        assert event.action == "create"
        assert event.object_id == access_request.id
        assert event.context == {"email": REQUESTER_EMAIL}
        assert "Geheime toelichting" not in str(event.context)

    def test_ops_channel_is_notified_without_name_or_address(self):
        self._login_without_account()

        self._post()

        self.send_ops_message.assert_called_once()
        message = self.send_ops_message.call_args.args[0]
        assert ADMIN_URL in message
        assert REQUESTER_EMAIL not in message
        assert "Nora" not in message

    def test_mattermost_failure_does_not_break_post(self):
        self.send_ops_message.side_effect = requests.RequestException
        self._login_without_account()

        response = self._post()

        assert response["Location"] == NO_ACCESS_URL
        assert AccessRequest.objects.count() == 1

    def test_logout_drops_the_claims(self):
        self._login_without_account()

        self.client.post("/uitloggen/")

        self.assertNotContains(self.client.get(NO_ACCESS_URL), SHEET_BUTTON)
        assert self._post().status_code == 302
        assert not AccessRequest.objects.exists()


@override_settings(ALLOWED_EMAIL_DOMAINS=ALLOWED_DOMAINS, STAFF_EMAILS=[STAFF_EMAIL])
class AdminAccessPerRoleTest(TestCase):
    """Only the Gebruikersbeheerder sees and decides; everyone else lands on /geen-toegang/."""

    def setUp(self):
        setup_roles()
        self.access_request = make_pending()
        self.routes = [
            ADMIN_URL,
            reverse("access-request-approve", args=[self.access_request.public_id]),
            reverse("access-request-reject", args=[self.access_request.public_id]),
        ]

    def _denied_users(self):
        consultant = grant_consultant(User.objects.create_user(email="consultant@rijksoverheid.nl"))
        business_manager = grant_business_manager(User.objects.create_user(email="bm@rijksoverheid.nl"))
        staff = make_staff_user()
        return {"Consultant": consultant, "Business Manager": business_manager, "Applicatiebeheerder": staff}

    def test_user_admin_may_open_every_route(self):
        self.client.force_login(make_user_admin())

        for route in self.routes:
            with self.subTest(route=route):
                assert self.client.get(route).status_code == 200

    def test_other_roles_are_sent_to_no_access(self):
        for role, user in self._denied_users().items():
            self.client.force_login(user)
            for route in self.routes:
                for method in ("get", "post"):
                    with self.subTest(role=role, route=route, method=method):
                        response = getattr(self.client, method)(route)
                        assert response.status_code == 302
                        assert response["Location"].startswith(NO_ACCESS_URL)

        self.access_request.refresh_from_db()
        assert self.access_request.status == AccessRequest.Status.PENDING

    def test_anonymous_is_sent_to_login(self):
        for route in self.routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                assert response.status_code == 302
                assert response["Location"].startswith("/inloggen/")

    def test_no_access_page_for_logged_in_user_says_missing_role(self):
        self.client.force_login(self._denied_users()["Consultant"])

        response = self.client.get(NO_ACCESS_URL)

        self.assertContains(response, "Geen toegang tot deze pagina")
        self.assertNotContains(response, SHEET_BUTTON)

    def test_admin_list_shows_pending_request(self):
        self.client.force_login(make_user_admin())

        response = self.client.get(ADMIN_URL)

        self.assertContains(response, "Open (1)")
        self.assertContains(response, "Nora Nieuw")
        self.assertContains(response, REQUESTER_EMAIL)

    def test_sidebar_counter_for_user_admin_only_when_pending(self):
        self.client.force_login(make_user_admin())

        response = self.client.get(reverse("admin-users"))
        self.assertContains(response, '1<span class="wies-visually-hidden"> open</span>')
        self.assertContains(response, "1 toegangsaanvraag wacht op beoordeling")

        self.access_request.status = AccessRequest.Status.REJECTED
        self.access_request.decided_at = timezone.now()
        self.access_request.save()

        response = self.client.get(reverse("admin-users"))
        self.assertContains(response, ADMIN_URL)
        self.assertNotContains(response, "> open</span>")
        self.assertNotContains(response, "wacht op beoordeling")

    def test_no_counter_or_link_for_applicatiebeheerder(self):
        self.client.force_login(make_staff_user())

        response = self.client.get(reverse("staff-dashboard"))

        assert response.status_code == 200
        self.assertNotContains(response, ADMIN_URL)
        self.assertNotContains(response, 'accessible-label="1 open"')

    def test_no_link_for_consultant_or_business_manager(self):
        for role, user in self._denied_users().items():
            if role == "Applicatiebeheerder":
                continue
            self.client.force_login(user)
            with self.subTest(role=role):
                self.assertNotContains(self.client.get(reverse("home"), follow=True), ADMIN_URL)


@override_settings(ALLOWED_EMAIL_DOMAINS=ALLOWED_DOMAINS, STAFF_EMAILS=[])
class ApproveTest(TestCase):
    def setUp(self):
        setup_roles()
        self.admin = make_user_admin()
        self.client.force_login(self.admin)
        self.suborganization = Suborganization.objects.create(name="Onderdeel A")
        self.access_request = make_pending(suborganization=self.suborganization)
        self.url = reverse("access-request-approve", args=[self.access_request.public_id])

    def _post(self, **data):
        return self.client.post(self.url, {"first_name": "Nora", "last_name": "Nieuw", **data})

    def test_get_prefills_the_request_with_email_locked(self):
        response = self.client.get(self.url)

        self.assertContains(response, 'value="Nora"')
        self.assertContains(response, REQUESTER_EMAIL)
        self.assertContains(response, "Toegangsaanvraag goedkeuren")
        # Rendered disabled, so the field does not look editable while the server ignores it.
        assert re.search(r'<nldd-text-field type="email" name="email"[^>]*\sdisabled[\s>]', response.content.decode())

    def test_approve_creates_user_and_colleague_with_roles(self):
        consultant = Group.objects.get(name=ROLE_CONSULTANT)
        business_manager = Group.objects.get(name=ROLE_BUSINESS_MANAGER)

        response = self._post(
            groups=[consultant.id, business_manager.id],
            suborganization=self.suborganization.public_id,
        )

        assert response.status_code == 200
        assert response["HX-Redirect"] == ADMIN_URL
        user = User.objects.get(email=REQUESTER_EMAIL)
        assert set(user.groups.values_list("name", flat=True)) == {ROLE_CONSULTANT, ROLE_BUSINESS_MANAGER}
        assert user.colleague.suborganization == self.suborganization
        self.access_request.refresh_from_db()
        assert self.access_request.status == AccessRequest.Status.APPROVED
        assert self.access_request.decided_by == self.admin
        assert self.access_request.created_user == user
        assert self.access_request.decided_at is not None

    def test_email_comes_from_the_request_not_the_post(self):
        self._post(email="kaper@rijksoverheid.nl")

        assert User.objects.filter(email=REQUESTER_EMAIL).exists()
        assert not User.objects.filter(email="kaper@rijksoverheid.nl").exists()

    def test_invalid_post_keeps_request_pending(self):
        response = self._post(first_name="")

        assert response.status_code == 200
        self.assertContains(response, "Voornaam is verplicht")
        assert not User.objects.filter(email=REQUESTER_EMAIL).exists()
        self.access_request.refresh_from_db()
        assert self.access_request.status == AccessRequest.Status.PENDING

    def test_approving_a_decided_request_goes_back_to_the_list(self):
        """A second beheerder clicking the same request learns it was handled; htmx shows nothing for a 404."""
        self._post()

        for response in (self.client.get(self.url, headers={"hx-request": "true"}), self._post()):
            assert response["HX-Redirect"] == ADMIN_URL
        assert User.objects.filter(email__iexact=REQUESTER_EMAIL).count() == 1
        self.assertContains(self.client.get(ADMIN_URL), "is al afgehandeld")

    def test_approved_request_shows_as_decided(self):
        self._post()

        response = self.client.get(ADMIN_URL)

        self.assertContains(response, "Open (0)")
        self.assertContains(response, "Goedgekeurd")
        self.assertContains(response, f"mailto:{REQUESTER_EMAIL}?")

    def test_requester_sees_no_form_after_approval(self):
        """The new account on the address wins: no new request on it."""
        self._post()
        self.client.logout()
        session = self.client.session
        session["failed_login_email"] = REQUESTER_EMAIL
        session["failed_login_claims"] = {"email": REQUESTER_EMAIL, "given_name": "", "family_name": ""}
        session.save()

        self.assertContains(self.client.get(NO_ACCESS_URL), "Er bestaat al een account")

    def test_user_create_sheet_closes_pending_request(self):
        response = self.client.post(
            reverse("user-create"),
            {"first_name": "Nora", "last_name": "Nieuw", "email": REQUESTER_EMAIL.upper()},
        )

        assert response.status_code in (200, 302)
        user = User.objects.get(email__iexact=REQUESTER_EMAIL)
        self.access_request.refresh_from_db()
        assert self.access_request.status == AccessRequest.Status.APPROVED
        assert self.access_request.created_user == user
        assert self.access_request.decided_by == self.admin
        [message] = get_messages(response.wsgi_request)
        assert "De toegangsaanvraag van Nora is daarmee goedgekeurd." in str(message)

    def test_user_create_sheet_without_request_says_nothing_about_one(self):
        response = self.client.post(
            reverse("user-create"),
            {"first_name": "Ander", "last_name": "Iemand", "email": "ander@rijksoverheid.nl"},
        )

        [message] = get_messages(response.wsgi_request)
        assert str(message) == "Gebruiker Ander Iemand is toegevoegd."

    def test_csv_import_closes_pending_request(self):
        result = create_users_from_csv(self.admin, f"first_name,last_name,email\nNora,Nieuw,{REQUESTER_EMAIL}\n")

        assert result["success"], result
        assert result["access_requests_approved"] == 1
        self.access_request.refresh_from_db()
        assert self.access_request.status == AccessRequest.Status.APPROVED
        assert self.access_request.created_user.email == REQUESTER_EMAIL

    def test_creating_another_user_leaves_request_pending(self):
        create_user(self.admin, first_name="Ander", last_name="Iemand", email="ander@rijksoverheid.nl")

        self.access_request.refresh_from_db()
        assert self.access_request.status == AccessRequest.Status.PENDING


@override_settings(ALLOWED_EMAIL_DOMAINS=ALLOWED_DOMAINS, STAFF_EMAILS=[])
class RejectTest(TestCase):
    def setUp(self):
        setup_roles()
        self.admin = make_user_admin()
        self.client.force_login(self.admin)
        self.access_request = make_pending()
        self.url = reverse("access-request-reject", args=[self.access_request.public_id])

    def test_reject_sets_status_reason_and_decider(self):
        response = self.client.post(self.url, {"decision_note": "Niet bij ODI"})

        assert response.status_code == 200
        assert response["HX-Redirect"] == ADMIN_URL
        self.access_request.refresh_from_db()
        assert self.access_request.status == AccessRequest.Status.REJECTED
        assert self.access_request.decision_note == "Niet bij ODI"
        assert self.access_request.decided_by == self.admin
        assert self.access_request.decided_at is not None
        assert not User.objects.filter(email=REQUESTER_EMAIL).exists()

    def test_reject_logs_an_update_event(self):
        self.client.post(self.url, {"decision_note": "Niet bij ODI"})

        event = Event.objects.get(object_type="AccessRequest", action="update")
        assert event.user == self.admin
        assert event.context == {"status": "rejected"}

    def test_reject_without_reason_is_allowed(self):
        self.client.post(self.url, {"decision_note": ""})

        self.access_request.refresh_from_db()
        assert self.access_request.status == AccessRequest.Status.REJECTED
        assert self.access_request.decision_note == ""

    def test_reason_over_500_characters_is_a_form_error(self):
        response = self.client.post(self.url, {"decision_note": "x" * 501})

        assert response.status_code == 200
        self.assertContains(response, "500 tekens")
        self.access_request.refresh_from_db()
        assert self.access_request.status == AccessRequest.Status.PENDING

    def test_rejecting_a_decided_request_goes_back_to_the_list(self):
        self.client.post(self.url, {"decision_note": ""})

        assert self.client.post(self.url, {"decision_note": "Nogmaals"})["HX-Redirect"] == ADMIN_URL
        self.access_request.refresh_from_db()
        assert self.access_request.decision_note == ""

    def test_a_decision_made_meanwhile_is_not_overwritten(self):
        """Two beheerders past the pending check at once: the second decision changes nothing."""
        stale = AccessRequest.objects.get(pk=self.access_request.pk)
        assert reject(self.access_request, self.admin, "Eerste")

        assert not reject(stale, self.admin, "Tweede")
        approve(stale, make_user_admin("ander@rijksoverheid.nl"), self.admin)

        self.access_request.refresh_from_db()
        assert self.access_request.decision_note == "Eerste"
        assert self.access_request.created_user is None
        assert Event.objects.filter(object_type="AccessRequest", action="update").count() == 1

    def test_decided_requests_past_retention_are_purged_on_list_load(self):
        now = timezone.now()
        old = make_pending(
            "oud@rijksoverheid.nl",
            status=AccessRequest.Status.REJECTED,
            decided_at=now - DECIDED_RETENTION - timedelta(days=1),
        )
        recent = make_pending(
            "recent@rijksoverheid.nl",
            status=AccessRequest.Status.APPROVED,
            decided_at=now - DECIDED_RETENTION + timedelta(days=1),
        )
        old_pending = make_pending("wacht@rijksoverheid.nl", created_at=now - timedelta(days=200))

        response = self.client.get(ADMIN_URL)

        assert response.status_code == 200
        assert not AccessRequest.objects.filter(pk=old.pk).exists()
        assert AccessRequest.objects.filter(pk=recent.pk).exists()
        assert AccessRequest.objects.filter(pk=old_pending.pk).exists()
        assert AccessRequest.objects.filter(pk=self.access_request.pk).exists()


@override_settings(ALLOWED_EMAIL_DOMAINS=ALLOWED_DOMAINS, STAFF_EMAILS=[])
@override_settings(EMAIL_ENABLED=True, SITE_BASE_URL="https://wies.example")
class DecisionMailTest(TestCase):
    """With the ZAD mail relay configured, the person hears the decision by mail."""

    def setUp(self):
        setup_roles()
        self.client.force_login(make_user_admin())
        self.access_request = make_pending()

    def _approve(self, **mail):
        url = reverse("access-request-approve", args=[self.access_request.public_id])
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(url, {"first_name": "Nora", "last_name": "Nieuw", **(mail or SEND_MAIL)})

    def _reject(self, note="", **mail):
        url = reverse("access-request-reject", args=[self.access_request.public_id])
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(url, {"decision_note": note, **(mail or SEND_MAIL)})

    def test_the_mail_checkbox_is_checked_by_default(self):
        for name in ("access-request-approve", "access-request-reject"):
            with self.subTest(name=name):
                response = self.client.get(reverse(name, args=[self.access_request.public_id]))

                assert re.search(r'<nldd-checkbox-field name="send_mail"[^>]*\schecked', response.content.decode())

    def test_unchecked_approving_mails_nothing(self):
        response = self._approve(send_mail="")

        assert mail.outbox == []
        assert User.objects.filter(email=REQUESTER_EMAIL).exists()
        [message] = get_messages(response.wsgi_request)
        assert str(message) == "Nora Nieuw heeft nu toegang tot Wies."

    def test_unchecked_rejecting_mails_nothing(self):
        self._reject("Geen ODI-collega", send_mail="")

        assert mail.outbox == []
        self.access_request.refresh_from_db()
        assert self.access_request.status == AccessRequest.Status.REJECTED

    def test_approving_mails_the_login_link(self):
        self._approve()

        [message] = mail.outbox
        assert message.to == [REQUESTER_EMAIL]
        assert message.reply_to == ["wies-odi@rijksoverheid.nl"]
        assert message.subject == "Je hebt toegang tot Wies"
        assert "https://wies.example/inloggen/" in message.body

    def test_the_approval_mail_uses_the_name_the_beheerder_confirmed(self):
        url = reverse("access-request-approve", args=[self.access_request.public_id])
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, {"first_name": "Noor", "last_name": "Nieuwe", **SEND_MAIL})

        assert mail.outbox[0].body.startswith("Hoi Noor,")
        [message] = get_messages(response.wsgi_request)
        assert str(message) == "Noor Nieuwe heeft nu toegang tot Wies. Noor krijgt hierover een e-mail."

    def test_rejecting_mails_the_reason(self):
        self._reject("Geen ODI-collega")

        [message] = mail.outbox
        assert message.subject == "Je toegangsaanvraag voor Wies is afgewezen"
        assert "Geen ODI-collega" in message.body
        assert "Je kunt opnieuw toegang aanvragen via http" in message.body

    def test_a_failing_relay_keeps_the_decision(self):
        with patch("django.core.mail.EmailMessage.send", side_effect=OSError("relay down")):
            response = self._reject()

        assert response["HX-Redirect"] == ADMIN_URL
        self.access_request.refresh_from_db()
        assert self.access_request.status == AccessRequest.Status.REJECTED

    def test_a_refused_recipient_is_logged_without_the_address(self):
        refused = smtplib.SMTPRecipientsRefused({REQUESTER_EMAIL: (550, b"unknown")})
        with (
            patch("django.core.mail.EmailMessage.send", side_effect=refused),
            self.assertLogs("wies.core.services.access_requests", "WARNING") as logs,
        ):
            self._reject()

        assert logs.output
        assert REQUESTER_EMAIL not in "\n".join(logs.output)

    def test_user_create_sheet_says_the_requester_gets_mail(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("user-create"),
                {"first_name": "Nora", "last_name": "Nieuw", "email": REQUESTER_EMAIL},
            )

        [message] = get_messages(response.wsgi_request)
        assert str(message).endswith("Nora krijgt hierover een e-mail.")
        assert [m.to for m in mail.outbox] == [[REQUESTER_EMAIL]]

    def test_the_beheer_page_drops_the_mailto(self):
        self._approve()

        self.assertNotContains(self.client.get(ADMIN_URL), "mailto:" + REQUESTER_EMAIL + "?")

    def test_without_the_relay_nothing_is_mailed(self):
        with override_settings(EMAIL_ENABLED=False):
            self._approve()

        assert mail.outbox == []

    def test_without_the_relay_there_is_no_mail_checkbox(self):
        with override_settings(EMAIL_ENABLED=False):
            response = self.client.get(reverse("access-request-approve", args=[self.access_request.public_id]))

        self.assertNotContains(response, 'name="send_mail"')


class AccessRequestPublicIdTest(TestCase):
    """The decision routes resolve by public_id; the integer PK never does."""

    def setUp(self):
        setup_roles()
        self.client.force_login(make_user_admin())
        self.access_request = make_pending()

    def test_new_request_gets_a_public_id(self):
        assert self.access_request.public_id is not None
        assert make_pending("ander@rijksoverheid.nl").public_id != self.access_request.public_id

    def test_integer_pk_routes_are_404(self):
        for action in ("goedkeuren", "afwijzen"):
            with self.subTest(action=action):
                url = f"{ADMIN_URL}{self.access_request.pk}/{action}/"
                assert self.client.get(url).status_code == 404

    def test_unknown_public_id_is_404(self):
        for name in ("access-request-approve", "access-request-reject"):
            with self.subTest(name=name):
                url = reverse(name, args=["00000000-0000-0000-0000-000000000000"])
                assert self.client.get(url).status_code == 404


@override_settings(EMAIL_ENABLED=True, SITE_BASE_URL="https://wies.example")
class DecisionMailFailureTest(TransactionTestCase):
    """A real commit, so the mail is tried before the beheerder's message is written."""

    def setUp(self):
        setup_roles()
        self.client.force_login(make_user_admin())
        self.access_request = make_pending()

    def _post(self, name, data):
        url = reverse(name, args=[self.access_request.public_id])
        with patch("django.core.mail.EmailMessage.send", side_effect=OSError("relay down")):
            response = self.client.post(url, {**data, **SEND_MAIL})
        [message] = get_messages(response.wsgi_request)
        return message

    def test_rejecting_says_the_mail_did_not_go_out(self):
        message = self._post("access-request-reject", {"decision_note": ""})

        assert message.level_tag == "warning"
        assert str(message) == (
            "De toegangsaanvraag van Nora Nieuw is afgewezen. "
            "De e-mail aan Nora kon niet worden verstuurd. Laat het Nora zelf weten."
        )

    def test_approving_says_the_mail_did_not_go_out(self):
        message = self._post("access-request-approve", {"first_name": "Nora", "last_name": "Nieuw"})

        assert message.level_tag == "warning"
        assert str(message).endswith("De e-mail aan Nora kon niet worden verstuurd. Laat het Nora zelf weten.")
        assert User.objects.filter(email=REQUESTER_EMAIL).exists()
