"""Who may grant which role (the grant matrix in ``features/roles.md``)."""

from django.contrib.auth.models import Group
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from wies.core.forms import UserForm
from wies.core.models import Event
from wies.core.roles import (
    ASSIGNMENT_ADMIN_GROUP_NAME,
    BDM_GROUP_NAME,
    USER_ADMIN_GROUP_NAME,
    setup_roles,
)
from wies.core.services.users import create_users_from_csv, update_user
from wies.rijksauth.models import User

STAFF_EMAIL = "platform@rijksoverheid.nl"
HX = {"HX-Request": "true"}


@override_settings(STAFF_EMAILS=[STAFF_EMAIL])
class RoleGrantTest(TestCase):
    def setUp(self):
        setup_roles()
        self.user_admin_group = Group.objects.get(name=USER_ADMIN_GROUP_NAME)
        self.assignment_admin_group = Group.objects.get(name=ASSIGNMENT_ADMIN_GROUP_NAME)
        self.consultant_group = Group.objects.get(name="Consultant")
        self.bdm_group = Group.objects.get(name=BDM_GROUP_NAME)

        # Gebruikersbeheer, not platform administration.
        self.user_admin = User.objects.create_user(
            email="gebruikersbeheer@rijksoverheid.nl", first_name="G", last_name="B"
        )
        self.user_admin.groups.add(self.user_admin_group)

        # Platform administration; also holds Gebruikersbeheer to reach the user views.
        self.staff = User.objects.create_user(email=STAFF_EMAIL, first_name="P", last_name="B")
        self.staff.groups.add(self.user_admin_group)

        self.target = User.objects.create_user(email="target@rijksoverheid.nl", first_name="T", last_name="G")
        self.client = Client()

    def _payload(self, user, groups):
        return {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "groups": [g.pk for g in groups],
        }

    def _group_names(self, user):
        return set(user.groups.values_list("name", flat=True))

    def test_user_admin_does_not_see_privileged_roles(self):
        names = set(UserForm(editor=self.user_admin).fields["groups"].queryset.values_list("name", flat=True))
        assert names == {"Consultant", BDM_GROUP_NAME}

    def test_staff_sees_every_role(self):
        names = set(UserForm(editor=self.staff).fields["groups"].queryset.values_list("name", flat=True))
        assert {USER_ADMIN_GROUP_NAME, ASSIGNMENT_ADMIN_GROUP_NAME} <= names

    def test_form_without_editor_hides_privileged_roles(self):
        names = set(UserForm().fields["groups"].queryset.values_list("name", flat=True))
        assert USER_ADMIN_GROUP_NAME not in names
        assert ASSIGNMENT_ADMIN_GROUP_NAME not in names

    def test_rendered_edit_form_hides_privileged_roles_from_user_admin(self):
        self.target.groups.add(self.assignment_admin_group)
        self.client.force_login(self.user_admin)

        response = self.client.get(reverse("user-edit", args=[self.target.public_id]), headers=HX)

        assert response.status_code == 200
        self.assertNotContains(response, ASSIGNMENT_ADMIN_GROUP_NAME)
        self.assertNotContains(response, USER_ADMIN_GROUP_NAME)
        self.assertContains(response, BDM_GROUP_NAME)

    def test_rendered_edit_form_shows_privileged_roles_to_staff(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("user-edit", args=[self.target.public_id]), headers=HX)

        self.assertContains(response, ASSIGNMENT_ADMIN_GROUP_NAME)
        self.assertContains(response, USER_ADMIN_GROUP_NAME)

    def test_rendered_create_form_shows_privileged_roles_only_to_staff(self):
        for editor, shown in ((self.staff, True), (self.user_admin, False)):
            with self.subTest(editor=editor.email):
                self.client.force_login(editor)

                response = self.client.get(reverse("user-create"), headers=HX)

                assert response.status_code == 200
                assert (ASSIGNMENT_ADMIN_GROUP_NAME in response.content.decode()) is shown
                self.assertContains(response, BDM_GROUP_NAME)

    def test_smuggled_privileged_role_fails_validation(self):
        for group in (self.user_admin_group, self.assignment_admin_group):
            with self.subTest(group=group.name):
                form = UserForm(self._payload(self.target, [group]), instance=self.target, editor=self.user_admin)
                assert not form.is_valid()
                assert "groups" in form.errors

    def test_smuggled_role_over_http_is_not_granted(self):
        self.client.force_login(self.user_admin)
        for user, group in (
            (self.target, self.assignment_admin_group),
            (self.target, self.user_admin_group),
            (self.user_admin, self.assignment_admin_group),  # self-elevation
        ):
            with self.subTest(user=user.email, group=group.name):
                response = self.client.post(
                    reverse("user-edit", args=[user.public_id]), self._payload(user, [group]), headers=HX
                )
                assert response.status_code == 200
                assert "HX-Redirect" not in response
                assert not user.groups.filter(pk=group.pk).exists()

    def test_smuggled_role_on_create_is_not_granted(self):
        self.client.force_login(self.user_admin)
        new = User(first_name="N", last_name="U", email="new@rijksoverheid.nl")

        response = self.client.post(reverse("user-create"), self._payload(new, [self.user_admin_group]), headers=HX)

        assert "HX-Redirect" not in response
        assert not User.objects.filter(email="new@rijksoverheid.nl").exists()

    def test_user_admin_may_grant_consultant_and_bdm(self):
        self.client.force_login(self.user_admin)

        response = self.client.post(
            reverse("user-edit", args=[self.target.public_id]),
            self._payload(self.target, [self.consultant_group, self.bdm_group]),
            headers=HX,
        )

        assert response["HX-Redirect"] == reverse("admin-users")
        assert self._group_names(self.target) == {"Consultant", BDM_GROUP_NAME}

    def test_user_admin_may_create_with_consultant_and_bdm(self):
        self.client.force_login(self.user_admin)
        new = User(first_name="N", last_name="U", email="new@rijksoverheid.nl")

        response = self.client.post(
            reverse("user-create"), self._payload(new, [self.consultant_group, self.bdm_group]), headers=HX
        )

        assert response["HX-Redirect"] == reverse("admin-users")
        assert self._group_names(User.objects.get(email="new@rijksoverheid.nl")) == {"Consultant", BDM_GROUP_NAME}

    def test_user_admin_edit_preserves_privileged_roles(self):
        self.target.groups.add(self.assignment_admin_group, self.user_admin_group, self.bdm_group)
        self.client.force_login(self.user_admin)

        # The form never offered the privileged roles, so they are not submitted.
        response = self.client.post(
            reverse("user-edit", args=[self.target.public_id]),
            self._payload(self.target, [self.consultant_group]),
            headers=HX,
        )

        assert response["HX-Redirect"] == reverse("admin-users")
        assert self._group_names(self.target) == {"Consultant", ASSIGNMENT_ADMIN_GROUP_NAME, USER_ADMIN_GROUP_NAME}
        event = Event.objects.filter(object_type="User", action="update").last()
        assert set(event.context["group_names"]) == self._group_names(self.target)

    def test_staff_grants_assignment_admin_with_event(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("user-edit", args=[self.target.public_id]),
            self._payload(self.target, [self.assignment_admin_group]),
            headers=HX,
        )

        assert response["HX-Redirect"] == reverse("admin-users")
        assert self._group_names(self.target) == {ASSIGNMENT_ADMIN_GROUP_NAME}
        event = Event.objects.filter(object_type="User", action="update").last()
        assert event.object_id == self.target.id
        assert event.user_id == self.staff.id
        assert event.context["group_names"] == [ASSIGNMENT_ADMIN_GROUP_NAME]

    def test_staff_creates_user_with_privileged_roles(self):
        self.client.force_login(self.staff)
        new = User(first_name="N", last_name="U", email="new@rijksoverheid.nl")

        response = self.client.post(
            reverse("user-create"),
            self._payload(new, [self.assignment_admin_group, self.user_admin_group]),
            headers=HX,
        )

        assert response["HX-Redirect"] == reverse("admin-users")
        assert self._group_names(User.objects.get(email="new@rijksoverheid.nl")) == {
            ASSIGNMENT_ADMIN_GROUP_NAME,
            USER_ADMIN_GROUP_NAME,
        }

    def test_staff_revokes_own_assignment_admin(self):
        # The "switch it off and test as a normal user" workflow.
        self.staff.groups.add(self.assignment_admin_group)
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("user-edit", args=[self.staff.public_id]),
            self._payload(self.staff, [self.user_admin_group]),
            headers=HX,
        )

        assert response["HX-Redirect"] == reverse("admin-users")
        assert self._group_names(self.staff) == {USER_ADMIN_GROUP_NAME}

    def _update(self, updater, groups):
        update_user(
            updater=updater,
            user=self.target,
            first_name="T",
            last_name="G",
            email=self.target.email,
            groups=groups,
        )

    def test_service_drops_privileged_roles_from_non_staff(self):
        self._update(self.user_admin, [self.assignment_admin_group, self.user_admin_group, self.consultant_group])
        assert self._group_names(self.target) == {"Consultant"}

    def test_service_without_updater_cannot_grant_privileged_roles(self):
        self._update(None, [self.assignment_admin_group])
        assert self._group_names(self.target) == set()

    def test_service_lets_staff_grant_privileged_roles(self):
        self._update(self.staff, [self.assignment_admin_group, self.user_admin_group])
        assert self._group_names(self.target) == {ASSIGNMENT_ADMIN_GROUP_NAME, USER_ADMIN_GROUP_NAME}

    def test_csv_import_by_non_staff_does_not_grant_user_admin(self):
        csv_content = (
            f"first_name,last_name,email,brand,{USER_ADMIN_GROUP_NAME},Consultant,BDM\n"
            "John,Doe,john.doe@rijksoverheid.nl,,y,y,n\n"
        )

        result = create_users_from_csv(self.user_admin, csv_content)

        assert result["success"], result
        assert self._group_names(User.objects.get(email="john.doe@rijksoverheid.nl")) == {"Consultant"}

    def test_csv_import_by_staff_grants_user_admin(self):
        csv_content = (
            f"first_name,last_name,email,brand,{USER_ADMIN_GROUP_NAME},Consultant,BDM\n"
            "John,Doe,john.doe@rijksoverheid.nl,,y,n,n\n"
        )

        result = create_users_from_csv(self.staff, csv_content)

        assert result["success"], result
        assert self._group_names(User.objects.get(email="john.doe@rijksoverheid.nl")) == {USER_ADMIN_GROUP_NAME}
