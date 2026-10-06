"""Who may grant which role (the grant matrix in ``features/roles.md``)."""

import re
from types import SimpleNamespace
from unittest import mock

import pytest
from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from wies.core.forms import UserForm
from wies.core.models import Event
from wies.core.roles import (
    ROLE_BUSINESS_MANAGER,
    ROLE_CONSULTANT,
    ROLE_STAFF,
    ROLE_USER_ADMIN,
    may_grant,
    role_label,
    setup_roles,
)
from wies.core.services.users import create_users_from_csv, update_user
from wies.rijksauth.models import User

from .inline_edit_helpers import post_inline_edit

STAFF_EMAIL = "applicatiebeheer@rijksoverheid.nl"
# In STAFF_EMAILS with no account behind it yet: the address a create can claim.
FREE_STAFF_EMAIL = "tweede-applicatiebeheer@rijksoverheid.nl"
HX = {"HX-Request": "true"}


def _labels_in_order(content: str) -> list[str]:
    """The role labels of a rendered roles sheet, in the order they are shown."""
    return [m.group(1) for m in re.finditer(r'<nldd-checkbox-field[^>]*label="([^"]*)"', content)]


def _ticked(content: str) -> set[str]:
    """The role labels a rendered roles sheet arrives with already checked."""
    boxes = re.finditer(r'<nldd-checkbox-field[^>]*label="([^"]*)"([^>]*)>', content)
    return {label for label, rest in (m.groups() for m in boxes) if "checked" in rest}


@override_settings(STAFF_EMAILS=[STAFF_EMAIL])
class RoleGrantTest(TestCase):
    """Roles are set from the users page, by whoever may grant them."""

    def setUp(self):
        setup_roles()
        self.user_admin_group = Group.objects.get(name=ROLE_USER_ADMIN)
        self.consultant_group = Group.objects.get(name=ROLE_CONSULTANT)
        self.business_manager_group = Group.objects.get(name=ROLE_BUSINESS_MANAGER)

        # Gebruikersbeheerder, not application administration.
        self.user_admin = User.objects.create_user(
            email="gebruikersbeheer@rijksoverheid.nl", first_name="G", last_name="B"
        )
        self.user_admin.groups.add(self.user_admin_group)

        # Application administration and nothing else: it runs the platform and
        # holds nothing on users or roles.
        self.staff = User.objects.create_user(email=STAFF_EMAIL, first_name="P", last_name="B")

        self.target = User.objects.create_user(email="target@rijksoverheid.nl", first_name="T", last_name="G")
        self.client = Client()

    def _roles_url(self, user):
        return reverse("user-edit", args=[user.public_id])

    def _group_names(self, user):
        return set(user.groups.values_list("name", flat=True))

    def _post_roles(self, user, groups):
        """The sheet posts one form, so the person rides along unchanged."""
        payload = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "groups": [g.pk for g in groups],
        }
        return self.client.post(self._roles_url(user), payload, headers=HX)

    def _post_create(self, email, groups):
        """Creating posts the same form as editing, so the roles ride along here too."""
        payload = {
            "first_name": "Nieuw",
            "last_name": "Account",
            "email": email,
            "groups": [g.pk for g in groups],
        }
        return self.client.post(reverse("user-create"), payload, headers=HX)

    def _offered(self, editor):
        return set(UserForm(editor=editor).fields["groups"].queryset.values_list("name", flat=True))

    def test_the_user_sheet_carries_the_person_and_the_roles(self):
        self.client.force_login(self.user_admin)

        content = self.client.get(reverse("user-edit", args=[self.target.public_id]), headers=HX).content.decode()

        assert 'label="Voornaam"' in content
        assert 'label="Rollen"' in content

    def test_editing_the_person_saves_the_roles_in_the_same_submission(self):
        self.target.groups.add(self.business_manager_group)
        self.client.force_login(self.user_admin)
        payload = {
            "first_name": "T",
            "last_name": "G",
            "email": self.target.email,
            "groups": [self.consultant_group.pk],
        }

        response = self.client.post(reverse("user-edit", args=[self.target.public_id]), payload, headers=HX)

        assert response["HX-Redirect"] == reverse("admin-users")
        # Saving replaces the whole set: Business Manager was offered and left out, so it goes.
        assert self._group_names(self.target) == {ROLE_CONSULTANT}

    def test_every_editor_is_offered_every_role(self):
        """No role is restricted to a granter of its own, and the Applicatiebeheerder is
        not a group, so it cannot be offered at all."""
        for editor in (self.user_admin, self.staff, None):
            with self.subTest(editor=getattr(editor, "email", "system")):
                assert self._offered(editor) == {ROLE_CONSULTANT, ROLE_BUSINESS_MANAGER, ROLE_USER_ADMIN}

    def test_application_administration_reaches_neither_the_page_nor_the_sheet(self):
        """It runs the platform and holds nothing functional. The way into a fresh
        environment is ``ensure_initial_user``, which creates its account with every
        role, not a right handed to the address list."""
        self.client.force_login(self.staff)

        assert self.client.get(reverse("admin-users")).status_code == 403
        assert self.client.get(self._roles_url(self.target), headers=HX).status_code == 403

    def test_a_reader_is_offered_no_action_they_cannot_carry_out(self):
        """``view_user`` opens the list; Bewerken, Nieuwe gebruiker and Verwijderen
        each ask their own permission, in the template as well as on the route."""
        reader = User.objects.create_user(email="lezer@rijksoverheid.nl")
        reader.user_permissions.add(Permission.objects.get(codename="view_user"))
        self.client.force_login(reader)

        content = self.client.get(reverse("admin-users")).content.decode()

        for name, url in (
            ("user-edit", self._roles_url(self.target)),
            ("user-create", reverse("user-create")),
            ("user-delete", reverse("user-delete", args=[self.target.public_id])),
        ):
            with self.subTest(route=name):
                assert url not in content, "offered an action the visitor cannot carry out"
                assert self.client.get(url, headers=HX).status_code == 403

    def test_the_row_menu_never_ends_in_a_divider(self):
        """Bewerken and Verwijderen are each withheld on their own gate, so the
        dividers between them have to move with them: a reader who may only look
        would otherwise get a menu that closes on a line with nothing under it."""
        reader = User.objects.create_user(email="lezer@rijksoverheid.nl")
        reader.user_permissions.add(Permission.objects.get(codename="view_user"))

        for viewer in (reader, self.user_admin):
            with self.subTest(viewer=viewer.email):
                self.client.force_login(User.objects.get(pk=viewer.pk))

                content = self.client.get(reverse("admin-users")).content.decode()

                # The row menu, by the slot it hangs in: ``<nldd-menu-item>`` shares
                # its prefix, and the utility menu nests one menu inside another.
                menus = re.findall(r'<nldd-menu slot="popup".*?</nldd-menu>', content, re.S)
                assert menus, "no row menu rendered at all"
                for menu in menus:
                    tags = re.findall(r"<nldd-menu-(item|divider)[ >]", menu)
                    assert tags, "an action menu with nothing in it"
                    assert tags[-1] == "item", "the menu ends in a divider"
                    assert "dividerdivider" not in "".join(tags), "two dividers in a row"

    def test_the_users_page_is_closed_without_either_authority(self):
        consultant = User.objects.create_user(email="consultant@rijksoverheid.nl")
        consultant.groups.add(self.consultant_group)
        self.client.force_login(consultant)

        assert self.client.get(reverse("admin-users")).status_code == 403

    def test_without_either_authority_the_user_sheet_is_closed(self):
        consultant = User.objects.create_user(email="consultant@rijksoverheid.nl")
        consultant.groups.add(self.consultant_group)
        self.client.force_login(consultant)

        assert self.client.get(self._roles_url(self.target)).status_code == 403
        self._post_roles(self.target, [self.consultant_group])
        assert self._group_names(self.target) == set()

    def test_the_rendered_sheet_never_offers_application_administration(self):
        """It follows the email address, so a checkbox for it would be a lie."""
        self.client.force_login(self.user_admin)

        response = self.client.get(self._roles_url(self.target), headers=HX)

        assert response.status_code == 200
        self.assertNotContains(response, role_label(ROLE_STAFF))
        self.assertContains(response, role_label(ROLE_USER_ADMIN))
        self.assertContains(response, role_label(ROLE_BUSINESS_MANAGER))

    def test_the_sheet_arrives_with_the_roles_the_user_already_holds(self):
        """Saving replaces the whole set, so a sheet that opens unticked strips
        every role the moment someone presses Opslaan."""
        self.target.groups.add(self.consultant_group, self.business_manager_group)
        self.client.force_login(self.user_admin)

        response = self.client.get(self._roles_url(self.target), headers=HX)

        assert _ticked(response.content.decode()) == {
            role_label(ROLE_CONSULTANT),
            role_label(ROLE_BUSINESS_MANAGER),
        }

    def test_the_sheet_lists_the_roles_by_label(self):
        """By key ``business_manager`` would come first, so the order pins the label sort."""
        self.client.force_login(self.user_admin)

        content = self.client.get(self._roles_url(self.target), headers=HX).content.decode()

        assert _labels_in_order(content) == [
            role_label(ROLE_BUSINESS_MANAGER),
            role_label(ROLE_CONSULTANT),
            role_label(ROLE_USER_ADMIN),
        ]

    def test_a_group_without_a_label_keeps_its_own_name(self):
        """A group an older version left behind has no entry in ``ROLE_LABELS``.
        It still has members and is still offered, so it has to stay readable
        instead of rendering as a nameless checkbox."""
        Group.objects.get_or_create(name="support")
        self.client.force_login(self.user_admin)

        content = self.client.get(self._roles_url(self.target), headers=HX).content.decode()

        assert "support" in _labels_in_order(content), "the leftover group has no name on the sheet"

    def test_the_sheet_opens_whole_and_a_rejected_submission_returns_the_body_only(self):
        """A POST reaches the sheet template only on a validation error; a whole
        sheet back then stacks a second one over the one that is already open."""
        self.client.force_login(self.user_admin)

        opened = self.client.get(self._roles_url(self.target), headers=HX).content.decode()

        assert "<nldd-sheet" in opened, "the user sheet did not come back as a sheet"
        assert "data-auto-show" in opened, "dialog.js has nothing to open after the swap"
        assert f'hx-post="{self._roles_url(self.target)}"' in opened, "the sheet posts somewhere else"

        rejected = self.client.post(
            self._roles_url(self.target),
            {"first_name": "", "last_name": "G", "email": self.target.email},
            headers=HX,
        ).content.decode()

        assert "<nldd-form>" in rejected, "the error re-render dropped the form"
        assert "<nldd-sheet" not in rejected, "a second sheet stacks over the open one"

    def test_the_beheer_menu_offers_no_page_the_visitor_cannot_open(self):
        """Read off a page the visitor actually opened.

        Application administration gets a 403 on the users page, and the refusal
        page renders the Beheer sidebar and the utility menu as well, so a body read
        from there is the menu of a page this visitor never reached. The roles page
        is the one it may open, and ``view_user`` is exactly what it does not hold,
        so the users entry has to be withheld in both menus or it links to a 403.
        """
        behind_user_admin = (reverse("admin-users"), reverse("label-admin"), reverse("suborganization-admin"))
        self.client.force_login(self.staff)

        content = self.client.get(reverse("role-matrix")).content.decode()

        assert f' href="{reverse("role-matrix")}"' in content, "the Beheer sidebar did not render at all"
        assert f'data-href="{reverse("role-matrix")}"' in content, "the utility menu's Beheer section did not render"
        for url in behind_user_admin:
            with self.subTest(url=url, visitor=role_label(ROLE_STAFF)):
                assert self.client.get(url).status_code == 403
                assert url not in content

        self.client.force_login(self.user_admin)
        content = self.client.get(reverse("admin-users")).content.decode()
        for url in behind_user_admin:
            with self.subTest(url=url, visitor=role_label(ROLE_USER_ADMIN)):
                assert url in content

    def test_reading_the_roles_is_not_granting_them(self):
        """``rijksauth.view_user`` opens the role matrix but not the screen that
        changes roles, so the two menus must offer the one and not the other."""
        reader = User.objects.create_user(email="lezer@rijksoverheid.nl", first_name="L", last_name="Z")
        reader.user_permissions.add(Permission.objects.get(codename="view_user"))
        self.client.force_login(reader)

        content = self.client.get(reverse("admin-users")).content.decode()

        assert f' href="{reverse("role-matrix")}"' in content, "the sidebar withheld Rollen from a view_user reader"
        assert f'data-href="{reverse("role-matrix")}"' in content, "the utility menu withheld Rollen"
        assert self._roles_url(self.target) not in content, "offered Bewerken to someone who may not grant roles"

        assert self.client.get(self._roles_url(self.target)).status_code == 403

    def test_granting_the_roles_is_not_reading_them(self):
        """The mirror of the case above: ``rijksauth.change_user`` opens the sheet
        that changes roles, and neither the matrix nor the list it usually hangs off."""
        granter = User.objects.create_user(email="toekenner@rijksoverheid.nl", first_name="T", last_name="K")
        granter.user_permissions.add(Permission.objects.get(codename="change_user"))
        self.client.force_login(granter)

        assert self.client.get(self._roles_url(self.target), headers=HX).status_code == 200
        assert self.client.get(reverse("admin-users")).status_code == 403
        assert self.client.get(reverse("role-matrix")).status_code == 302

    def test_the_matrix_points_a_granter_at_the_users_page(self):
        """The matrix says which role may what, the users page hands them out, so
        whoever may do both must be able to get from the one to the other."""
        self.client.force_login(self.user_admin)

        content = self.client.get(reverse("role-matrix")).content.decode()

        # The sidebar carries the same url on an ``nldd-list-item``; the page's own
        # sentence is the only one that renders it as an ``<a>``.
        assert f'<a href="{reverse("admin-users")}">Gebruikers</a>' in content, (
            "the matrix withheld the users page from someone who may grant roles"
        )

    def test_superusers_are_not_on_the_users_page(self):
        """Same exclusion as the user list: no role lands on the one account that
        bypasses them anyway."""
        superuser = User.objects.create_user(
            email="su@rijksoverheid.nl", first_name="S", last_name="U", is_superuser=True
        )
        self.client.force_login(self.user_admin)

        content = self.client.get(reverse("admin-users")).content.decode()

        assert superuser.email not in content
        assert self.client.get(self._roles_url(superuser), headers=HX).status_code == 404
        assert self._post_roles(superuser, [self.consultant_group]).status_code == 404
        assert self._group_names(superuser) == set()

    def test_a_group_id_that_is_not_a_role_is_refused(self):
        """The queryset the form offers is also what a submitted id is validated
        against, so a hand-built POST cannot reach a group it never showed."""
        gone = Group.objects.create(name="verwijderd")
        form = UserForm({"groups": [gone.pk]}, instance=self.target, editor=self.user_admin)
        gone.delete()

        assert not form.is_valid()
        assert "groups" in form.errors

    def test_user_admin_may_grant_consultant_and_bdm(self):
        self.client.force_login(self.user_admin)

        response = self._post_roles(self.target, [self.consultant_group, self.business_manager_group])

        assert response["HX-Redirect"] == reverse("admin-users")
        assert self._group_names(self.target) == {ROLE_CONSULTANT, ROLE_BUSINESS_MANAGER}

    def test_saving_replaces_the_whole_set(self):
        self.target.groups.add(self.user_admin_group, self.business_manager_group)
        self.client.force_login(self.user_admin)

        response = self._post_roles(self.target, [self.consultant_group])

        assert response["HX-Redirect"] == reverse("admin-users")
        assert self._group_names(self.target) == {ROLE_CONSULTANT}
        event = Event.objects.filter(object_type="User", action="update").last()
        assert event.context["group_names"] == [role_label(ROLE_CONSULTANT)]

    def test_user_admin_grants_and_revokes_user_admin(self):
        """The Gebruikersbeheerder hands itself on, which is why onboarding does not stall
        on an application administrator."""
        self.client.force_login(self.user_admin)

        granted = self._post_roles(self.target, [self.user_admin_group])

        assert granted["HX-Redirect"] == reverse("admin-users")
        assert self._group_names(self.target) == {ROLE_USER_ADMIN}

        revoked = self._post_roles(self.target, [])

        assert revoked["HX-Redirect"] == reverse("admin-users")
        assert self._group_names(self.target) == set()

    def test_a_user_admin_grants_bdm_with_event(self):
        self.client.force_login(self.user_admin)

        response = self._post_roles(self.target, [self.business_manager_group])

        assert response["HX-Redirect"] == reverse("admin-users")
        assert self._group_names(self.target) == {ROLE_BUSINESS_MANAGER}
        event = Event.objects.filter(object_type="User", action="update").last()
        assert event.object_id == self.target.id
        assert event.user_id == self.user_admin.id
        assert event.context["group_names"] == [role_label(ROLE_BUSINESS_MANAGER)]

    def test_an_editor_revokes_their_own_bdm(self):
        # The "switch it off and test as a normal user" workflow.
        self.user_admin.groups.add(self.business_manager_group)
        self.client.force_login(self.user_admin)

        response = self._post_roles(self.user_admin, [self.user_admin_group])

        assert response["HX-Redirect"] == reverse("admin-users")
        assert self._group_names(self.user_admin) == {ROLE_USER_ADMIN}

    def test_users_page_lists_users_with_their_roles(self):
        self.target.groups.add(self.consultant_group)
        self.client.force_login(self.user_admin)

        content = self.client.get(reverse("admin-users")).content.decode()

        assert self.target.email in content
        assert f'text="{role_label(ROLE_CONSULTANT)}"' in content
        assert f'text="{ROLE_CONSULTANT}"' not in content
        assert self._roles_url(self.target) in content

    def test_the_service_sets_the_roles_it_is_given(self):
        update_user(
            updater=self.user_admin,
            user=self.target,
            first_name=self.target.first_name,
            last_name=self.target.last_name,
            email=self.target.email,
            groups=[self.business_manager_group, self.user_admin_group],
        )
        assert self._group_names(self.target) == {ROLE_BUSINESS_MANAGER, ROLE_USER_ADMIN}

    def test_creating_a_user_grants_the_roles_that_were_ticked(self):
        """The sheet hands out roles on create as well as on edit, so a new
        colleague arrives with them instead of needing a second pass over the row
        menu. The event carries them, as it does for an edit."""
        self.client.force_login(self.user_admin)

        response = self._post_create("nieuw@rijksoverheid.nl", [self.consultant_group, self.business_manager_group])

        assert response["HX-Redirect"] == reverse("admin-users")
        created = User.objects.get(email="nieuw@rijksoverheid.nl")
        assert self._group_names(created) == {ROLE_CONSULTANT, ROLE_BUSINESS_MANAGER}
        event = Event.objects.filter(object_type="User", action="create").last()
        assert event.object_id == created.id
        # In label order: Business Manager before Consultant.
        assert event.context["group_names"] == [role_label(ROLE_BUSINESS_MANAGER), role_label(ROLE_CONSULTANT)]

    def test_the_beheer_menus_offer_the_users_page_to_whoever_may_open_it(self):
        """The entries ask the same ``view_user`` the page does, so a reader who may
        open it is offered it and does not need the url bar."""
        reader = User.objects.create_user(email="lezer2@rijksoverheid.nl", first_name="L", last_name="Z")
        reader.user_permissions.add(Permission.objects.get(codename="view_user"))
        sidebar_entry = f'<nldd-list-item href="{reverse("admin-users")}"'
        for viewer in (self.user_admin, reader):
            with self.subTest(viewer=viewer.email):
                self.client.force_login(User.objects.get(pk=viewer.pk))

                content = self.client.get(reverse("admin-users")).content.decode()

                assert sidebar_entry in content, "the Beheer sidebar withheld Gebruikers from someone who may open it"

        # The utility menu's whole Beheer section sits behind the role matrix gate,
        # so only a visitor who passes that one can be asked about the entry inside.
        self.client.force_login(User.objects.get(pk=self.user_admin.pk))

        content = self.client.get(reverse("admin-users")).content.decode()

        assert f'data-href="{reverse("admin-users")}"' in content, "the utility menu withheld Gebruikers"

    def test_csv_import_by_user_admin_grants_user_admin(self):
        """Every role column of the import is one the Gebruikersbeheerder may grant."""
        csv_content = (
            f"first_name,last_name,email,brand,{role_label(ROLE_USER_ADMIN)},{role_label(ROLE_CONSULTANT)},Business Manager\n"
            "John,Doe,john.doe@rijksoverheid.nl,,y,y,n\n"
        )

        result = create_users_from_csv(self.user_admin, csv_content)

        assert result["success"], result
        assert self._group_names(User.objects.get(email="john.doe@rijksoverheid.nl")) == {
            ROLE_USER_ADMIN,
            ROLE_CONSULTANT,
        }
        assert result["errors"] == []

    def test_csv_import_skips_an_existing_user_and_grants_the_other_rows(self):
        # Row 4 is skipped as an existing user; the rows around it still land.
        csv_content = (
            f"first_name,last_name,email,brand,{role_label(ROLE_USER_ADMIN)},{role_label(ROLE_CONSULTANT)},Business Manager\n"
            "Ann,Een,ann@rijksoverheid.nl,,y,n,n\n"
            "Bob,Twee,bob@rijksoverheid.nl,,n,y,n\n"
            f"Tom,Drie,{self.target.email},,y,n,n\n"
            "Eva,Vier,eva@rijksoverheid.nl,,Y,n,y\n"
        )

        result = create_users_from_csv(self.user_admin, csv_content)

        assert result["success"], result
        assert result["users_created"] == 3
        assert result["errors"] == [f"User with email '{self.target.email}' already exists, skipped"]
        assert self._group_names(User.objects.get(email="eva@rijksoverheid.nl")) == {
            ROLE_USER_ADMIN,
            ROLE_BUSINESS_MANAGER,
        }
        assert self._group_names(self.target) == set()

    def test_csv_role_columns_are_matched_however_the_header_is_written(self):
        """The header is a label typed by hand or by Excel, so case and padding
        around it may not decide whether a role column is seen at all."""
        csv_content = (
            f"first_name,last_name,email, {role_label(ROLE_USER_ADMIN).upper()} ,bdm\n"
            "John,Doe,john.doe@rijksoverheid.nl,y,y\n"
        )

        result = create_users_from_csv(self.user_admin, csv_content)

        assert result["success"], result
        assert self._group_names(User.objects.get(email="john.doe@rijksoverheid.nl")) == {
            ROLE_USER_ADMIN,
            ROLE_BUSINESS_MANAGER,
        }

    def test_csv_import_by_staff_grants_user_admin(self):
        csv_content = (
            f"first_name,last_name,email,brand,{role_label(ROLE_USER_ADMIN)},{role_label(ROLE_CONSULTANT)},Business Manager\n"
            "John,Doe,john.doe@rijksoverheid.nl,,y,n,n\n"
        )

        result = create_users_from_csv(self.staff, csv_content)

        assert result["success"], result
        assert self._group_names(User.objects.get(email="john.doe@rijksoverheid.nl")) == {ROLE_USER_ADMIN}
        assert result["errors"] == []


@override_settings(STAFF_EMAILS=[STAFF_EMAIL])
class StaffEmailChangeTest(TestCase):
    def setUp(self):
        setup_roles()
        user_admin_group = Group.objects.get(name=ROLE_USER_ADMIN)
        self.user_admin = User.objects.create_user(
            email="gebruikersbeheer@rijksoverheid.nl", first_name="G", last_name="B"
        )
        self.user_admin.groups.add(user_admin_group)
        self.staff = User.objects.create_user(email=STAFF_EMAIL, first_name="P", last_name="B")
        self.staff.groups.add(user_admin_group)
        self.client = Client()

    def _edit_email(self, user, email):
        payload = {"first_name": user.first_name, "last_name": user.last_name, "email": email}
        return self.client.post(reverse("user-edit", args=[user.public_id]), payload, headers=HX)

    def _inline_email(self, user, email):
        url = reverse("inline-edit", args=["user", user.public_id, "email"])
        return post_inline_edit(self.client, url, {"email": email}, headers=HX)

    def _email(self, user):
        user.refresh_from_db()
        return user.email

    def _set_email(self, user, email):
        User.objects.filter(pk=user.pk).update(email=email)

    def test_user_admin_cannot_move_staff_address_away(self):
        self.client.force_login(self.user_admin)
        for edit in (self._edit_email, self._inline_email):
            with self.subTest(route=edit.__name__):
                self._set_email(self.staff, STAFF_EMAIL)
                edit(self.staff, "weg@rijksoverheid.nl")
                assert self._email(self.staff) == STAFF_EMAIL

    def test_user_admin_cannot_take_over_staff_address(self):
        # The address is free, as after the move-away step of the bypass.
        self.staff.email = "weg@rijksoverheid.nl"
        self.staff.save()
        self.client.force_login(self.user_admin)
        for edit in (self._edit_email, self._inline_email):
            with self.subTest(route=edit.__name__):
                self._set_email(self.user_admin, "gebruikersbeheer@rijksoverheid.nl")
                edit(self.user_admin, STAFF_EMAIL)
                assert self._email(self.user_admin) == "gebruikersbeheer@rijksoverheid.nl"
        assert self.client.get(reverse("staff-database")).status_code != 200

    def test_user_admin_cannot_move_staff_address_stored_in_other_case(self):
        self._set_email(self.staff, "Applicatiebeheer@rijksoverheid.nl")
        self.client.force_login(self.user_admin)

        self._edit_email(self.staff, "weg@rijksoverheid.nl")

        assert self._email(self.staff) == "Applicatiebeheer@rijksoverheid.nl"

    def test_user_admin_may_edit_staff_user_keeping_the_address(self):
        self.client.force_login(self.user_admin)
        payload = {"first_name": "Nieuw", "last_name": "B", "email": STAFF_EMAIL}

        response = self.client.post(reverse("user-edit", args=[self.staff.public_id]), payload, headers=HX)

        assert response["HX-Redirect"] == reverse("admin-users")
        self.staff.refresh_from_db()
        assert (self.staff.first_name, self.staff.email) == ("Nieuw", STAFF_EMAIL)

    def test_edit_route_refuses_move_even_if_form_allows_it(self):
        self.client.force_login(self.user_admin)

        with mock.patch("wies.core.forms.may_change_email", return_value=True):
            response = self._edit_email(self.staff, "weg@rijksoverheid.nl")

        assert response.status_code == 403
        assert self._email(self.staff) == STAFF_EMAIL

    def test_form_shows_error_to_user_admin(self):
        self.client.force_login(self.user_admin)

        response = self._edit_email(self.staff, "weg@rijksoverheid.nl")

        assert "HX-Redirect" not in response
        self.assertContains(response, "Alleen de applicatiebeheerder mag dit e-mailadres wijzigen.")

    def _create(self, email):
        payload = {"first_name": "Nieuw", "last_name": "Account", "email": email}
        return self.client.post(reverse("user-create"), payload, headers=HX)

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL, FREE_STAFF_EMAIL])
    def test_user_admin_cannot_create_a_user_on_a_staff_address(self):
        """The other way onto an application administrator's address: not moving an
        account there, but being born there. ``FREE_STAFF_EMAIL`` is in the list with
        no account yet, so whoever fills it hands out application administration."""
        self.client.force_login(self.user_admin)

        response = self._create(FREE_STAFF_EMAIL)

        assert "HX-Redirect" not in response
        self.assertContains(response, "Alleen de applicatiebeheerder mag een gebruiker op dit e-mailadres aanmaken.")
        assert not User.objects.filter(email__iexact=FREE_STAFF_EMAIL).exists()

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL, FREE_STAFF_EMAIL])
    def test_staff_may_create_a_user_on_a_staff_address(self):
        self.client.force_login(self.staff)

        response = self._create(FREE_STAFF_EMAIL)

        assert response["HX-Redirect"] == reverse("admin-users")
        assert User.objects.filter(email__iexact=FREE_STAFF_EMAIL).exists()

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL, FREE_STAFF_EMAIL])
    def test_create_route_refuses_even_if_form_allows_it(self):
        self.client.force_login(self.user_admin)

        with mock.patch("wies.core.forms.may_change_email", return_value=True):
            response = self._create(FREE_STAFF_EMAIL)

        assert response.status_code == 403
        assert not User.objects.filter(email__iexact=FREE_STAFF_EMAIL).exists()

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL, FREE_STAFF_EMAIL])
    def test_the_csv_import_names_the_row_it_refuses(self):
        """Refused with the row number, alongside the other per-row checks: the
        create itself refuses too, but from inside the atomic block, which would
        roll the whole file back without saying which line was the problem."""
        csv_content = f"first_name,last_name,email\nAnn,Een,ann@rijksoverheid.nl\nBob,Twee,{FREE_STAFF_EMAIL}\n"

        result = create_users_from_csv(self.user_admin, csv_content)

        assert not result["success"]
        assert result["errors"] == [f"Row 3: only application administration may create a user on '{FREE_STAFF_EMAIL}'"]
        # Row 2 is fine and still does not land: a row error stops the whole file,
        # as it does for an unknown merk or a bad domain.
        assert result["users_created"] == 0
        assert not User.objects.filter(email__iexact="ann@rijksoverheid.nl").exists()
        assert not User.objects.filter(email__iexact=FREE_STAFF_EMAIL).exists()

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL, FREE_STAFF_EMAIL])
    def test_the_csv_import_lets_staff_through(self):
        csv_content = f"first_name,last_name,email\nBob,Twee,{FREE_STAFF_EMAIL}\n"

        result = create_users_from_csv(self.staff, csv_content)

        assert result["success"], result
        assert User.objects.filter(email__iexact=FREE_STAFF_EMAIL).exists()

    def test_the_inline_route_is_closed_to_everyone(self):
        target = User.objects.create_user(email="target@rijksoverheid.nl", first_name="T", last_name="G")

        for editor in (self.user_admin, self.staff):
            with self.subTest(editor=editor.email):
                self.client.force_login(editor)
                self._inline_email(target, "nieuw@rijksoverheid.nl")
                assert self._email(target) == "target@rijksoverheid.nl"

    def test_user_admin_may_change_other_addresses(self):
        target = User.objects.create_user(email="target@rijksoverheid.nl", first_name="T", last_name="G")
        self.client.force_login(self.user_admin)

        response = self._edit_email(target, "nieuw@rijksoverheid.nl")

        assert response["HX-Redirect"] == reverse("admin-users")
        assert self._email(target) == "nieuw@rijksoverheid.nl"

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL, "tweede@rijksoverheid.nl"])
    def test_staff_may_move_staff_addresses(self):
        target = User.objects.create_user(email="target@rijksoverheid.nl", first_name="T", last_name="G")
        self.client.force_login(self.staff)

        self._edit_email(target, "tweede@rijksoverheid.nl")
        assert self._email(target) == "tweede@rijksoverheid.nl"
        self._edit_email(self.staff, "weg@rijksoverheid.nl")
        assert self._email(self.staff) == "weg@rijksoverheid.nl"

    def test_service_refuses_non_staff_updater(self):
        for updater in (self.user_admin, None):
            with self.subTest(updater=updater), pytest.raises(PermissionDenied):
                update_user(
                    updater=updater, user=self.staff, first_name="P", last_name="B", email="weg@rijksoverheid.nl"
                )
        assert self._email(self.staff) == STAFF_EMAIL

        self.staff.email = "weg@rijksoverheid.nl"
        self.staff.save()
        with pytest.raises(PermissionDenied):
            update_user(updater=self.user_admin, user=self.user_admin, first_name="G", last_name="B", email=STAFF_EMAIL)
        assert self._email(self.user_admin) == "gebruikersbeheer@rijksoverheid.nl"


class MayGrantTest(SimpleTestCase):
    """``may_grant`` is the one place the policy lives, so ask it about any role."""

    def test_every_role_is_grantable_by_anyone_on_the_screen(self):
        for role in (ROLE_CONSULTANT, ROLE_BUSINESS_MANAGER, ROLE_USER_ADMIN):
            with self.subTest(role=role):
                assert may_grant(None, role) is True

    @override_settings(STAFF_EMAILS=["app@rijksoverheid.nl"])
    def test_application_administration_itself_is_never_grantable(self):
        """It is an address list, not a group: no editor, however privileged, hands
        it on from inside the application."""
        editor = SimpleNamespace(is_authenticated=True, email="app@rijksoverheid.nl")

        assert may_grant(editor, ROLE_STAFF) is False


@override_settings(STAFF_EMAILS=[STAFF_EMAIL])
class TheWayIntoAFreshEnvironmentTest(TestCase):
    """What ``features/roles.md`` rests on where it says the Applicatiebeheerder needs
    nothing on users or roles: the first user of an environment is created with
    every role, so somebody can administer users without the address list being
    handed a functional right.

    ``ensure_initial_user`` skips an account that already exists, so the claim is
    only as good as "a login cannot get there first". It cannot: the OIDC backend
    claims an account, it never creates one. For an environment that already has
    accounts, the way in comes from ``rijksauth/0012`` and ``0013`` instead, which
    hand every address in ``STAFF_EMAILS`` the Business Manager and
    Gebruikersbeheerder roles once (``rijksauth/tests/test_role_migrations.py``).
    """

    INITIAL = "eerste@rijksoverheid.nl"
    ENV = {
        "INITIAL_USER_EMAIL": INITIAL,
        "INITIAL_USER_FIRSTNAME": "Eerste",
        "INITIAL_USER_LASTNAME": "Gebruiker",
    }

    def setUp(self):
        setup_roles()

    def _bootstrap(self):
        with mock.patch.dict("os.environ", self.ENV):
            call_command("ensure_initial_user")

    def _sheet(self, user):
        return reverse("user-edit", args=[user.public_id])

    def test_the_initial_user_can_administer_users(self):
        """Not "holds a group" but "reaches the screens": the users page asks
        ``view_user`` and the sheet ``change_user``, and those are what the way in
        has to be."""
        self._bootstrap()

        user = User.objects.get(email=self.INITIAL)
        assert ROLE_USER_ADMIN in set(user.groups.values_list("name", flat=True))
        self.client.force_login(user)
        assert self.client.get(reverse("admin-users")).status_code == 200
        assert self.client.get(self._sheet(user), headers=HX).status_code == 200

    def test_every_role_the_screens_know_about(self):
        """Every group, so no role is left for somebody else to hand out first."""
        self._bootstrap()

        held = set(User.objects.get(email=self.INITIAL).groups.values_list("name", flat=True))
        assert held == {ROLE_CONSULTANT, ROLE_BUSINESS_MANAGER, ROLE_USER_ADMIN}

    def test_a_login_cannot_create_the_account_the_command_would_then_skip(self):
        """The one way the claim could fail: if signing in made the account, the
        command would find it and skip, and the environment would come up with
        nobody able to administer users."""
        signed_in = authenticate(request=None, username="verse-sub", email=self.INITIAL, email_verified=True)

        assert signed_in is None
        assert not User.objects.filter(email__iexact=self.INITIAL).exists()

        self._bootstrap()
        assert User.objects.get(email=self.INITIAL).groups.exists()

    def test_the_command_leaves_an_account_that_already_exists_alone(self):
        """The limit of the claim, stated: the command is a bootstrap, not a repair.
        An environment whose accounts predate it gets its way in from the migrations.
        """
        existing = User.objects.create_user(email=self.INITIAL, first_name="Al", last_name="Daar")

        self._bootstrap()

        assert User.objects.filter(email__iexact=self.INITIAL).count() == 1
        assert not User.objects.get(pk=existing.pk).groups.exists()
