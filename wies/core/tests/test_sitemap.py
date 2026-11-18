from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from wies.core.roles import ROLE_USER_ADMIN, setup_roles
from wies.core.tests.role_helpers import (
    STAFF_EMAIL,
    grant_business_manager,
    grant_consultant,
    make_business_manager_user,
    make_staff_user,
)
from wies.rijksauth.models import User

EVERYONE = [
    "home",
    "assignment-list",
    "user-profile",
    "handleiding",
    "faq",
    "contact",
    "privacy",
    "beveiliging",
    "toegankelijkheid",
]
BUSINESS_MANAGER = ["bezetting"]
USER_ADMIN = ["admin-users", "label-admin", "suborganization-admin", "role-matrix"]
STAFF = ["staff-dashboard", "staff-database"]
ALL = EVERYONE + BUSINESS_MANAGER + USER_ADMIN + STAFF


class SitemapTest(TestCase):
    def _hrefs(self, user) -> set[str]:
        self.client.force_login(user)
        response = self.client.get(reverse("sitemap"))
        assert response.status_code == 200
        content = response.content.decode()
        return {name for name in ALL if f'href="{reverse(name)}"' in content}

    def test_requires_login(self):
        response = self.client.get(reverse("sitemap"), follow=False)

        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))

    def test_consultant_sees_no_beheer(self):
        user = grant_consultant(User.objects.create_user(email="consultant@rijksoverheid.nl"))

        assert self._hrefs(user) == set(EVERYONE)
        assert "<h2>Beheer</h2>" not in self.client.get(reverse("sitemap")).content.decode()

    def test_business_manager_also_sees_bezetting(self):
        assert self._hrefs(make_business_manager_user()) == set(EVERYONE + BUSINESS_MANAGER)

    def test_user_admin_also_sees_beheer(self):
        user = User.objects.create_user(email="beheerder@rijksoverheid.nl")
        user.groups.add(Group.objects.get_or_create(name=ROLE_USER_ADMIN)[0])

        assert self._hrefs(user) == set(EVERYONE + USER_ADMIN)

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_staff_also_sees_maintenance_pages(self):
        assert self._hrefs(make_staff_user()) == set(EVERYONE + STAFF)

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_every_link_opens_for_its_user(self):
        """Each link the page offers must open for whoever it is offered to."""
        setup_roles()
        user = grant_business_manager(make_staff_user())
        user.groups.add(Group.objects.get_or_create(name=ROLE_USER_ADMIN)[0])

        hrefs = self._hrefs(user)

        assert hrefs == set(ALL)
        for name in hrefs:
            with self.subTest(name=name):
                assert self.client.get(reverse(name)).status_code == 200

    def test_footer_links_to_sitemap(self):
        self.client.force_login(User.objects.create_user(email="iemand@rijksoverheid.nl"))

        response = self.client.get(reverse("contact"))

        assert f'<a href="{reverse("sitemap")}">Sitemap</a>' in response.content.decode()
