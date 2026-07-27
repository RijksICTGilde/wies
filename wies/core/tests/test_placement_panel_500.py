from django.contrib.auth import get_user_model
from django.test import Client, TestCase

User = get_user_model()


class PlacementPanelInvalidParamTest(TestCase):
    """A non-numeric side-panel query param must not 500.

    The side-panel views (home placement list, assignment list, user profile)
    look up ?plaatsing=/?collega=/?opdracht= via Model.objects.get(id=<raw
    string>). A non-integer value fails PK coercion with ValueError; the lookups
    now catch it alongside DoesNotExist, so the request degrades to "no panel"
    instead of raising a 500.
    """

    def setUp(self):
        # raise_request_exception=False so an unexpected view exception surfaces
        # as a 500 response we can assert against, rather than being re-raised.
        self.client = Client(raise_request_exception=False)
        self.user = User.objects.create_user(email="test@rijksoverheid.nl", first_name="Test", last_name="User")
        self.client.force_login(self.user)

    def test_non_numeric_plaatsing_param_does_not_500(self):
        response = self.client.get("/", {"plaatsing": "x"})
        assert response.status_code == 200

    def test_non_numeric_collega_param_does_not_500(self):
        response = self.client.get("/", {"collega": "x"})
        assert response.status_code == 200

    def test_non_numeric_opdracht_param_does_not_500(self):
        response = self.client.get("/", {"opdracht": "x"})
        assert response.status_code == 200
