from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

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
        assert "Dummy data laden" in body

    @override_settings(ENABLE_DESTRUCTIVE_STAFF_ACTIONS=False)
    def test_buttons_hidden_when_disabled(self):
        response = self.client.get("/beheer/database/")

        assert response.status_code == 200
        body = response.content.decode()
        assert "Database leegmaken" not in body
        assert "Dummy data laden" not in body
        # Sync action stays visible.
        assert "Organisaties synchroniseren" in body

    @override_settings(ENABLE_DESTRUCTIVE_STAFF_ACTIONS=False)
    def test_clear_data_post_returns_403_and_does_not_delete(self):
        Assignment.objects.create(name="Should survive", source="wies")

        response = self.client.post("/beheer/database/", {"action": "clear_data"})

        assert response.status_code == 403
        assert Assignment.objects.filter(name="Should survive").exists()

    @override_settings(ENABLE_DESTRUCTIVE_STAFF_ACTIONS=False)
    def test_load_base_data_post_returns_403(self):
        response = self.client.post("/beheer/database/", {"action": "load_base_data"})

        assert response.status_code == 403

    @override_settings(ENABLE_DESTRUCTIVE_STAFF_ACTIONS=False)
    def test_sync_organizations_post_still_works(self):
        # Non-destructive action must not be blocked by the guard.
        response = self.client.post("/beheer/database/", {"action": "sync_organizations"}, follow=False)

        assert response.status_code != 403
