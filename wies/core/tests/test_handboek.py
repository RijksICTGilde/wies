from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from wies.core.handboek import HANDBOEK_PAGES
from wies.core.roles import setup_roles
from wies.core.tests.role_helpers import grant_consultant

User = get_user_model()


class HandboekTest(TestCase):
    def setUp(self):
        setup_roles()
        self.user = User.objects.create_user(email="consultant@rijksoverheid.nl", first_name="Con", last_name="Sultant")
        grant_consultant(self.user)
        self.client.force_login(self.user)

    def test_every_page_renders(self):
        for page in HANDBOEK_PAGES:
            with self.subTest(page=page.slug):
                response = self.client.get(page.path)

                assert response.status_code == 200

    def test_first_page_is_the_handbook_root(self):
        response = self.client.get(reverse("handboek"))

        self.assertContains(response, "<h1>Handboek: hoe we Wies bouwen</h1>", html=True)

    def test_unknown_page_is_not_found(self):
        response = self.client.get(reverse("handboek-page", args=["bestaat-niet"]))

        assert response.status_code == 404

    def test_menu_marks_the_current_page(self):
        html = self.client.get(reverse("handboek-page", args=["de-code"])).content.decode()

        assert '<strong aria-current="page">De code</strong>' in html
        assert 'text="**De code**"' in html
        assert f'href="{reverse("handboek-page", args=["visie"])}"' in html

    def test_menu_lists_the_sections_of_the_current_page_only(self):
        html = self.client.get(reverse("handboek-page", args=["de-code"])).content.decode()

        assert '<nldd-list-item slot="children" href="#rollen-en-rechten">' in html
        assert 'href="#wies-in-het-kort"' not in html

    def test_reachable_from_footer(self):
        html = self.client.get(reverse("user-profile")).content.decode()

        assert f'<a href="{reverse("handboek")}">Hoe we Wies bouwen</a>' in html
