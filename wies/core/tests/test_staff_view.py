from unittest.mock import patch

import requests
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from wies.core.models import Assignment

User = get_user_model()

STAFF_EMAIL = "staff@rijksoverheid.nl"


@override_settings(STAFF_EMAILS=[STAFF_EMAIL])
class StaffDestructiveActionsGuardTest(TestCase):
    """Verify that destructive /staff/ actions are guarded by ENABLE_DESTRUCTIVE_STAFF_ACTIONS."""

    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(email=STAFF_EMAIL, first_name="Staff", last_name="User")
        self.client.force_login(self.staff_user)

    @override_settings(ENABLE_DESTRUCTIVE_STAFF_ACTIONS=True)
    def test_buttons_visible_when_enabled(self):
        response = self.client.get("/beheer/database/")

        assert response.status_code == 200
        body = response.content.decode()
        assert "Database leegmaken" in body
        assert "Dummy data genereren" in body

    @override_settings(ENABLE_DESTRUCTIVE_STAFF_ACTIONS=False)
    def test_buttons_hidden_when_disabled(self):
        response = self.client.get("/beheer/database/")

        assert response.status_code == 200
        body = response.content.decode()
        assert "Database leegmaken" not in body
        assert "Dummy data genereren" not in body
        # Sync action stays visible.
        assert "Organisaties synchroniseren" in body

    @override_settings(ENABLE_DESTRUCTIVE_STAFF_ACTIONS=False)
    def test_clear_data_post_returns_405_and_does_not_delete(self):
        Assignment.objects.create(name="Should survive", source="wies")

        response = self.client.post("/beheer/database/", {"action": "clear_data"})

        assert response.status_code == 405
        assert Assignment.objects.filter(name="Should survive").exists()

    @override_settings(ENABLE_DESTRUCTIVE_STAFF_ACTIONS=False)
    def test_load_base_data_post_returns_405(self):
        response = self.client.post("/beheer/database/", {"action": "load_base_data"})

        assert response.status_code == 405

    @override_settings(ENABLE_DESTRUCTIVE_STAFF_ACTIONS=False)
    def test_sync_organizations_post_still_works(self):
        # Non-destructive action must not be blocked by the guard.
        response = self.client.post("/beheer/database/", {"action": "sync_organizations"}, follow=False)

        assert response.status_code != 405


@override_settings(STAFF_EMAILS=[STAFF_EMAIL])
class StaffResetOnboardingTest(TestCase):
    """Verify staff can reset their own onboarding flag from the database page."""

    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(email=STAFF_EMAIL, first_name="Staff", last_name="User")
        self.client.force_login(self.staff_user)

    @override_settings(ENABLE_DESTRUCTIVE_STAFF_ACTIONS=False)
    def test_reset_onboarding_card_always_visible(self):
        # The reset card is non-destructive and shows even when destructive actions are disabled.
        response = self.client.get("/beheer/database/")

        assert response.status_code == 200
        assert "Onboarding resetten" in response.content.decode()

    @override_settings(ENABLE_DESTRUCTIVE_STAFF_ACTIONS=False)
    def test_reset_onboarding_clears_flag(self):
        self.staff_user.onboarding_completed_at = timezone.now()
        self.staff_user.save(update_fields=["onboarding_completed_at"])

        response = self.client.post("/beheer/database/", {"action": "reset_onboarding"})

        assert response.status_code == 302
        self.staff_user.refresh_from_db()
        assert self.staff_user.onboarding_completed_at is None


@override_settings(
    STAFF_EMAILS=[STAFF_EMAIL],
    SITE_BASE_URL="https://wies.example",
    MATTERMOST_TOKEN="bot-token",
    MATTERMOST_WIES_OPS_CHANNEL_URL="https://mm.example/chat/odi/channels/wies-testing",
)
class StaffTestOpsNotificationTest(TestCase):
    """The button that posts the access request notification to check an environment's Mattermost setup."""

    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(email=STAFF_EMAIL, first_name="Staff", last_name="User")
        self.client.force_login(self.staff_user)
        patcher = patch("wies.core.views.staff.send_ops_message", return_value=True)
        self.send_ops_message = patcher.start()
        self.addCleanup(patcher.stop)

    def _post(self):
        response = self.client.post("/beheer/database/", {"action": "test_ops_notification"})
        return response, [str(m) for m in get_messages(response.wsgi_request)]

    def test_button_is_on_the_database_page(self):
        response = self.client.get("/beheer/database/")

        assert "Testmelding versturen" in response.content.decode()

    def test_posts_the_real_access_request_notification(self):
        response, msgs = self._post()

        assert response.status_code == 302
        self.send_ops_message.assert_called_once_with(
            "Nieuwe toegangsaanvraag voor Wies: https://wies.example/beheer/toegangsaanvragen/"
        )
        assert msgs == ["De melding is verstuurd naar het Mattermost-kanaal wies-testing."]

    def test_says_when_mattermost_is_not_configured(self):
        self.send_ops_message.return_value = False

        _response, msgs = self._post()

        assert msgs == ["Mattermost is niet ingesteld: het token of het kanaal ontbreekt."]

    def test_names_the_status_when_mattermost_refuses(self):
        refused = requests.Response()
        refused.status_code = 403
        self.send_ops_message.side_effect = requests.HTTPError(response=refused)

        _response, msgs = self._post()

        assert "fout 403" in msgs[0]

    def test_says_when_mattermost_is_unreachable(self):
        self.send_ops_message.side_effect = requests.ConnectionError

        _response, msgs = self._post()

        assert msgs == ["Mattermost is niet bereikbaar. Probeer het later opnieuw."]

    def test_non_staff_cannot_send(self):
        other = User.objects.create_user(email="gewoon@rijksoverheid.nl", first_name="Gewone", last_name="Gebruiker")
        self.client.force_login(other)

        response = self.client.post("/beheer/database/", {"action": "test_ops_notification"})

        assert response.status_code == 302
        assert response["Location"].startswith("/geen-toegang/")
        self.send_ops_message.assert_not_called()
