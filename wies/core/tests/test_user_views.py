from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Event, Label, LabelCategory, User


class UserViewsTest(TestCase):
    """Tests for user list, creation, and deletion views"""

    def setUp(self):
        """Create test data"""
        self.client = Client()

        # Create a regular user for authentication
        self.auth_user = User.objects.create(
            username="auth_user",
            email="auth@rijksoverheid.nl",
            first_name="Auth",
            last_name="User",
        )

        # Grant all user permissions to auth_user for existing tests
        view_permission = Permission.objects.get(codename="view_user")
        add_permission = Permission.objects.get(codename="add_user")
        change_permission = Permission.objects.get(codename="change_user")
        delete_permission = Permission.objects.get(codename="delete_user")
        self.auth_user.user_permissions.add(view_permission, add_permission, change_permission, delete_permission)

        # Create a superuser (should be excluded from list)
        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@rijksoverheid.nl",
            password="admin123",
            first_name="Admin",
            last_name="User",
        )

        # Create test labels
        self.category, _ = LabelCategory.objects.get_or_create(name="Merk", defaults={"color": "#0066CC"})
        self.label_a = Label.objects.create(name="Brand A", category=self.category)
        self.label_b = Label.objects.create(name="Brand B", category=self.category)

        # Create test groups for form testing
        self.admin_group = Group.objects.create(name="Beheerder")
        self.consultant_group = Group.objects.create(name="Consultant")
        self.bdm_group = Group.objects.create(name="Business Development Manager")

        # Create test users
        self.user1 = User.objects.create(
            username="user1",
            email="user1@rijksoverheid.nl",
            first_name="John",
            last_name="Doe",
        )
        self.user1.labels.add(self.label_a)

        self.user2 = User.objects.create(
            username="user2",
            email="user2@rijksoverheid.nl",
            first_name="Jane",
            last_name="Smith",
        )
        self.user2.labels.add(self.label_b)

    def test_user_admin_requires_login(self):
        """Test that user list requires authentication"""
        response = self.client.get(reverse("admin-users"), follow=False)
        assert response.status_code == 302
        assert response.url.startswith("/inloggen/")

    def test_user_admin_excludes_superusers(self):
        """Test that superusers are excluded from user list"""
        self.client.force_login(self.auth_user)
        response = self.client.get(reverse("admin-users"))

        assert response.status_code == 200

        # Check response content for user emails
        content = response.content.decode()

        # Regular users should be in the list
        assert self.user1.get_full_name() in content
        assert self.user2.get_full_name() in content
        assert self.auth_user.get_full_name() in content

        # Superuser should NOT be in the list
        assert self.superuser.get_full_name() not in content

    def test_user_admin_label_filter(self):
        """Test filtering users by label"""
        self.client.force_login(self.auth_user)

        # Filter by label A
        response = self.client.get(reverse("admin-users"), {"labels": self.label_a.id})
        content = response.content.decode()

        # user1 should be in results
        assert self.user1.get_full_name() in content
        # user2 should not be in results
        assert self.user2.get_full_name() not in content

    def test_user_admin_search(self):
        """Test searching users by name or email"""
        self.client.force_login(self.auth_user)

        # Search by first name
        response = self.client.get(reverse("admin-users"), {"zoek": "John"})
        content = response.content.decode()
        assert self.user1.get_full_name() in content
        assert self.user2.get_full_name() not in content

        # Search by email
        response = self.client.get(reverse("admin-users"), {"zoek": "jane"})
        content = response.content.decode()
        assert self.user2.get_full_name() in content
        assert self.user1.get_full_name() not in content

    def test_user_admin_search_full_name(self):
        """Test searching users by full name (first and last name together)"""
        self.client.force_login(self.auth_user)

        # Search by full name "John Doe" - this should find user1 but currently doesn't
        response = self.client.get(reverse("admin-users"), {"zoek": "John Doe"})
        content = response.content.decode()
        assert self.user1.get_full_name() in content
        assert self.user2.get_full_name() not in content

    def test_user_create_get_returns_form(self):
        """Test that GET to user-create returns the form modal"""
        self.client.force_login(self.auth_user)
        response = self.client.get(reverse("user-create"))

        assert response.status_code == 200
        content = response.content.decode()
        assert "modal-content" in content
        assert "Nieuwe gebruiker" in content

    def test_user_create_success(self):
        """Test successful user creation"""
        self.client.force_login(self.auth_user)

        initial_count = User.objects.filter(is_superuser=False).count()
        initial_event_count = Event.objects.count()

        response = self.client.post(
            reverse("user-create"),
            {
                "first_name": "New",
                "last_name": "User",
                "email": "newuser@rijksoverheid.nl",
                "category_Merk": self.label_a.id,
            },
        )

        # Should redirect to users list
        assert response.status_code == 302
        assert response.url == reverse("admin-users")

        # User should be created
        assert User.objects.filter(is_superuser=False).count() == initial_count + 1

        # Verify user details
        new_user = User.objects.get(email="newuser@rijksoverheid.nl")
        assert new_user.first_name == "New"
        assert new_user.last_name == "User"
        assert new_user.labels.filter(id=self.label_a.id).exists()
        assert not new_user.is_superuser

        # Event should be created
        assert Event.objects.count() == initial_event_count + 1
        created_event = Event.objects.last()
        assert created_event.name == "User.create"
        assert created_event.context["email"] == "newuser@rijksoverheid.nl"

    def test_user_create_without_labels(self):
        """Test user creation without labels (optional field)"""
        self.client.force_login(self.auth_user)

        response = self.client.post(
            reverse("user-create"),
            {
                "first_name": "No",
                "last_name": "Labels",
                "email": "nolabels@rijksoverheid.nl",
            },
        )

        # Should redirect to users list
        assert response.status_code == 302
        assert response.url == reverse("admin-users")

        new_user = User.objects.get(email="nolabels@rijksoverheid.nl")
        assert new_user.labels.count() == 0

    def test_user_create_validation_errors(self):
        """Test user creation with validation errors"""
        self.client.force_login(self.auth_user)

        # Missing required field
        response = self.client.post(
            reverse("user-create"),
            {
                "first_name": "Missing",
                # Missing last_name and email
            },
        )

        # Should return 200 with form errors (re-rendered modal)
        assert response.status_code == 200
        content = response.content.decode()
        # Modal should be shown with errors
        assert "modal-content" in content

    def test_user_create_duplicate_email(self):
        """Test that a new user cannot be created with an existing email"""
        self.client.force_login(self.auth_user)

        # Try to create a user with an email that already exists
        response = self.client.post(
            reverse("user-create"),
            {
                "first_name": "Duplicate",
                "last_name": "User",
                "email": "user1@rijksoverheid.nl",  # This email already exists (user1)
            },
        )

        # Should return 200 with form errors (re-rendered modal)
        assert response.status_code == 200
        content = response.content.decode()

        # Modal should be shown with errors
        assert "modal-content" in content
        # Should contain error message about duplicate email
        assert "email" in content.lower()

        # User should not be created
        assert User.objects.filter(email="user1@rijksoverheid.nl").count() == 1

    def test_user_create_requires_login(self):
        """Test that user creation requires authentication"""
        response = self.client.post(
            reverse("user-create"),
            {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@rijksoverheid.nl",
            },
        )

        assert response.status_code == 302
        assert response.url.startswith("/inloggen/")

    def test_user_delete_success(self):
        """Test successful user deletion"""
        self.client.force_login(self.auth_user)

        initial_count = User.objects.count()
        initial_event_count = Event.objects.count()

        user_id = self.user1.id
        response = self.client.post(reverse("user-delete", args=[user_id]))

        # Should return updated table (HTMX response)
        assert response.status_code == 200
        assert "HX-Redirect" in response

        # User should be deleted
        assert User.objects.count() == initial_count - 1
        assert not User.objects.filter(id=user_id).exists()

        # Event should be created
        assert Event.objects.count() == initial_event_count + 1
        created_event = Event.objects.last()
        assert created_event.context["id"] == user_id
        assert created_event.context["email"] == self.user1.email

    def test_user_delete_prevents_superuser_deletion(self):
        """Test that superusers cannot be deleted via this endpoint"""
        self.client.force_login(self.auth_user)

        response = self.client.post(reverse("user-delete", args=[self.superuser.id]))

        # Should return 404 (get_object_or_404 with is_superuser=False)
        assert response.status_code == 404

        # Superuser should still exist
        assert User.objects.filter(id=self.superuser.id).exists()

    def test_user_delete_nonexistent_user(self):
        """Test deletion of non-existent user returns 404"""
        self.client.force_login(self.auth_user)

        response = self.client.post(reverse("user-delete", args=[99999]))
        assert response.status_code == 404

    def test_user_delete_requires_login(self):
        """Test that user deletion requires authentication"""
        response = self.client.post(reverse("user-delete", args=[self.user1.id]))

        assert response.status_code == 302
        assert response.url.startswith("/inloggen/")

    # Permission tests
    def test_user_admin_requires_view_permission(self):
        """Test that user list returns 403 without view_user permission"""
        # Create user without view_user permission
        user_no_perms = User.objects.create(
            username="no_perms",
            email="noperms@rijksoverheid.nl",
            first_name="No",
            last_name="Perms",
        )
        self.client.force_login(user_no_perms)

        response = self.client.get(reverse("admin-users"))
        assert response.status_code == 403

    def test_user_admin_allows_with_view_permission(self):
        """Test that user list works with view_user permission"""
        user_with_perms = User.objects.create(
            username="with_perms",
            email="withperms@rijksoverheid.nl",
            first_name="With",
            last_name="Perms",
        )
        view_permission = Permission.objects.get(codename="view_user")
        user_with_perms.user_permissions.add(view_permission)
        self.client.force_login(user_with_perms)

        response = self.client.get(reverse("admin-users"))
        assert response.status_code == 200

    def test_user_create_requires_add_permission(self):
        """Test that user creation returns 403 without add_user permission"""
        # Create user with only view permission
        user_view_only = User.objects.create(
            username="view_only",
            email="viewonly@rijksoverheid.nl",
            first_name="View",
            last_name="Only",
        )
        view_permission = Permission.objects.get(codename="view_user")
        user_view_only.user_permissions.add(view_permission)
        self.client.force_login(user_view_only)

        # Try to create user
        response = self.client.post(
            reverse("user-create"),
            {
                "first_name": "New",
                "last_name": "User",
                "email": "newuser@rijksoverheid.nl",
            },
        )
        assert response.status_code == 403

        # User should not be created
        assert not User.objects.filter(email="newuser@rijksoverheid.nl").exists()

    def test_user_create_get_requires_add_permission(self):
        """Test that getting the user creation form returns 403 without add_user permission"""
        user_no_add = User.objects.create(
            username="no_add",
            email="noadd@rijksoverheid.nl",
            first_name="No",
            last_name="Add",
        )
        self.client.force_login(user_no_add)

        response = self.client.get(reverse("user-create"))
        assert response.status_code == 403

    def test_user_delete_requires_delete_permission(self):
        """Test that user deletion returns 403 without delete_user permission"""
        # Create user with only view permission
        user_view_only = User.objects.create(
            username="view_only2",
            email="viewonly2@rijksoverheid.nl",
            first_name="View",
            last_name="Only2",
        )
        view_permission = Permission.objects.get(codename="view_user")
        user_view_only.user_permissions.add(view_permission)
        self.client.force_login(user_view_only)

        initial_count = User.objects.count()

        # Try to delete user
        response = self.client.post(reverse("user-delete", args=[self.user1.id]))
        assert response.status_code == 403

        # User should not be deleted
        assert User.objects.count() == initial_count
        assert User.objects.filter(id=self.user1.id).exists()

    def test_user_edit_get_returns_form_with_data(self):
        """Test that GET to user-edit returns the form modal with user data"""
        self.client.force_login(self.auth_user)
        response = self.client.get(reverse("user-edit", args=[self.user1.id]))

        assert response.status_code == 200
        content = response.content.decode()
        assert "modal-content" in content
        assert "Gebruiker bewerken" in content
        # Check that form is pre-populated
        assert self.user1.first_name in content
        assert self.user1.last_name in content
        assert self.user1.email in content

    def test_user_edit_success(self):
        """Test successful user editing"""
        self.client.force_login(self.auth_user)

        initial_count_events = Event.objects.count()

        response = self.client.post(
            reverse("user-edit", args=[self.user1.id]),
            {
                "first_name": "Updated",
                "last_name": "Name",
                "email": "updated@rijksoverheid.nl",
            },
        )

        # Should redirect to users list
        assert response.status_code == 302
        assert response.url == reverse("admin-users")

        # User should be updated
        self.user1.refresh_from_db()
        assert self.user1.first_name == "Updated"
        assert self.user1.last_name == "Name"
        assert self.user1.email == "updated@rijksoverheid.nl"

        # Event should be created
        assert Event.objects.count() == initial_count_events + 1
        created_event = Event.objects.last()
        assert created_event.name == "User.update"
        assert created_event.context["email"] == "updated@rijksoverheid.nl"

    def test_user_edit_validation_errors(self):
        """Test user editing with validation errors"""
        self.client.force_login(self.auth_user)

        # Missing required field
        response = self.client.post(
            reverse("user-edit", args=[self.user1.id]),
            {
                "first_name": "Updated",
                # Missing last_name and email
            },
        )

        # Should return 200 with form errors (re-rendered modal)
        assert response.status_code == 200
        content = response.content.decode()
        # Modal should be shown with errors
        assert "modal-content" in content
        assert "Gebruiker bewerken" in content

        # User should not be updated
        self.user1.refresh_from_db()
        assert self.user1.first_name == "John"

    def test_user_edit_prevents_superuser_editing(self):
        """Test that superusers cannot be edited via this endpoint"""
        self.client.force_login(self.auth_user)

        response = self.client.post(
            reverse("user-edit", args=[self.superuser.id]),
            {
                "first_name": "Hacked",
                "last_name": "Admin",
                "email": "hacked@rijksoverheid.nl",
            },
        )

        # Should return 404 (get_object_or_404 with is_superuser=False)
        assert response.status_code == 404

        # Superuser should not be modified
        self.superuser.refresh_from_db()
        assert self.superuser.first_name == "Admin"

    def test_user_edit_nonexistent_user(self):
        """Test editing of non-existent user returns 404"""
        self.client.force_login(self.auth_user)

        response = self.client.get(reverse("user-edit", args=[99999]))
        assert response.status_code == 404

    def test_user_edit_requires_login(self):
        """Test that user editing requires authentication"""
        response = self.client.post(
            reverse("user-edit", args=[self.user1.id]),
            {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@rijksoverheid.nl",
            },
        )

        assert response.status_code == 302
        assert response.url.startswith("/inloggen/")

    def test_user_edit_requires_change_permission(self):
        """Test that user editing returns 403 without change_user permission"""
        # Create user with only view permission
        user_view_only = User.objects.create(
            username="view_only3",
            email="viewonly3@rijksoverheid.nl",
            first_name="View",
            last_name="Only3",
        )
        view_permission = Permission.objects.get(codename="view_user")
        user_view_only.user_permissions.add(view_permission)
        self.client.force_login(user_view_only)

        # Try to edit user
        response = self.client.post(
            reverse("user-edit", args=[self.user1.id]),
            {
                "first_name": "Unauthorized",
                "last_name": "Edit",
                "email": "unauthorized@rijksoverheid.nl",
            },
        )
        assert response.status_code == 403

        # User should not be updated
        self.user1.refresh_from_db()
        assert self.user1.first_name == "John"

    def test_user_edit_get_requires_change_permission(self):
        """Test that getting the user edit form returns 403 without change_user permission"""
        user_no_change = User.objects.create(
            username="no_change",
            email="nochange@rijksoverheid.nl",
            first_name="No",
            last_name="Change",
        )
        self.client.force_login(user_no_change)

        response = self.client.get(reverse("user-edit", args=[self.user1.id]))
        assert response.status_code == 403

    def test_user_create_uses_rvo_styling(self):
        """Test that user create/edit views use RVO design system styling"""
        self.client.force_login(self.auth_user)
        response = self.client.get(reverse("user-create"))

        assert response.status_code == 200
        content = response.content.decode()

        # Simple integration test - verify RVO classes are present
        assert "rvo-label" in content
        assert "utrecht-form-field" in content


class UserImportTest(TestCase):
    """Tests for CSV user import functionality"""

    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.import_url = reverse("user-import-csv")

        # Create test groups
        self.admin_group = Group.objects.create(name="Beheerder")
        self.consultant_group = Group.objects.create(name="Consultant")
        self.bdm_group = Group.objects.create(name="Business Development Manager")

        # Create test label
        category, _ = LabelCategory.objects.get_or_create(name="Merk", defaults={"color": "#0066CC"})
        self.existing_label = Label.objects.create(name="Existing Brand", category=category)

        # Create authenticated user with add_user permission
        self.auth_user = User.objects.create(
            username="testuser",
            email="test@rijksoverheid.nl",
            first_name="Test",
            last_name="User",
        )
        add_permission = Permission.objects.get(codename="add_user")
        self.auth_user.user_permissions.add(add_permission)

        # Create user without permissions
        self.no_perm_user = User.objects.create(
            username="nopermuser",
            email="noperm@rijksoverheid.nl",
            first_name="No",
            last_name="Permission",
        )

    def _create_csv_file(self, content):
        """Helper to create a CSV file upload"""
        return SimpleUploadedFile("users.csv", content.encode("utf-8"), content_type="text/csv")

    def test_import_requires_login(self):
        """Test that import endpoint requires authentication"""
        response = self.client.get(self.import_url)
        assert response.status_code == 302
        assert response.url.startswith("/inloggen/")

    def test_import_requires_add_permission(self):
        """Test that import requires add_user permission"""
        self.client.force_login(self.no_perm_user)
        response = self.client.get(self.import_url)
        assert response.status_code == 403

    def test_import_get_returns_form(self):
        """Test that GET request returns the import form"""
        self.client.force_login(self.auth_user)
        response = self.client.get(self.import_url)

        assert response.status_code == 200
        content = response.content.decode()
        assert "Gebruikers importeren" in content
        assert "csv_file" in content

    def test_import_requires_file_upload(self):
        """Test that import requires a file to be uploaded"""
        self.client.force_login(self.auth_user)
        response = self.client.post(self.import_url, {})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Geen bestand geüpload" in content

    def test_import_validates_csv_file_type(self):
        """Test that import validates file is a CSV"""
        self.client.force_login(self.auth_user)
        txt_file = SimpleUploadedFile("users.txt", b"not a csv", content_type="text/plain")

        response = self.client.post(self.import_url, {"csv_file": txt_file})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Ongeldig bestandstype" in content

    def test_import_valid_csv_creates_users(self):
        """Test successful import of valid CSV with users"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email,brand,Beheerder,Consultant,BDM
John,Doe,john.doe@rijksoverheid.nl,Brand A,y,n,n
Jane,Smith,jane.smith@rijksoverheid.nl,Brand B,n,y,n"""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(self.import_url, {"csv_file": csv_file})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Import geslaagd" in content
        assert "2" in content  # 2 users created
        assert "Brand A" in content
        assert "Brand B" in content

        # Verify users were created
        john = User.objects.get(email="john.doe@rijksoverheid.nl")
        assert john.first_name == "John"
        assert john.last_name == "Doe"
        # Verify label was assigned (Brand A should be created as label)
        assert john.labels.filter(name="Brand A").exists()
        assert john.groups.filter(name="Beheerder").exists()
        assert not john.groups.filter(name="Consultant").exists()

        jane = User.objects.get(email="jane.smith@rijksoverheid.nl")
        assert jane.first_name == "Jane"
        assert jane.groups.filter(name="Consultant").exists()
        assert not jane.groups.filter(name="Beheerder").exists()

    def test_import_reuses_existing_labels(self):
        """Test that import reuses existing labels instead of creating duplicates"""
        self.client.force_login(self.auth_user)
        csv_content = f"""first_name,last_name,email,brand,Administrator,Consultant,BDM
John,Doe,john.doe@rijksoverheid.nl,{self.existing_label.name},n,n,n"""
        csv_file = self._create_csv_file(csv_content)

        label_count_before = Label.objects.count()

        response = self.client.post(self.import_url, {"csv_file": csv_file})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Import geslaagd" in content
        assert Label.objects.count() == label_count_before

        john = User.objects.get(email="john.doe@rijksoverheid.nl")
        assert john.labels.filter(id=self.existing_label.id).exists()

    def test_import_validates_missing_required_columns(self):
        """Test that import validates required columns are present"""
        self.client.force_login(self.auth_user)
        csv_content = "first_name,last_name\nJohn,Doe"
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(self.import_url, {"csv_file": csv_file})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Import mislukt" in content
        assert "Missing required columns" in content
        assert "email" in content

    def test_import_validates_missing_required_fields(self):
        """Test that import validates required fields have values"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email
John,,john@rijksoverheid.nl
,Doe,jane@rijksoverheid.nl"""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(self.import_url, {"csv_file": csv_file})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Import mislukt" in content
        assert "Row 2" in content
        assert "last_name" in content
        assert "Row 3" in content
        assert "first_name" in content

    def test_import_validates_email_format(self):
        """Test that import validates email format"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email
John,Doe,invalid-email
Jane,Smith,also-invalid"""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(self.import_url, {"csv_file": csv_file})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Import mislukt" in content
        assert "invalid email format" in content

    def test_import_validates_group_values(self):
        """Test that import validates group columns have 'y' or 'n' values"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email,brand,Beheerder,Consultant,BDM
John,Doe,john@rijksoverheid.nl,Brand A,yes,n,n
Jane,Smith,jane@rijksoverheid.nl,Brand B,y,maybe,n"""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(self.import_url, {"csv_file": csv_file})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Import mislukt" in content
        assert "Beheerder" in content
        assert "must be" in content
        assert "Consultant" in content

    def test_import_detects_duplicate_emails_in_csv(self):
        """Test that import detects duplicate emails within the CSV"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email
John,Doe,duplicate@rijksoverheid.nl
Jane,Smith,duplicate@rijksoverheid.nl"""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(self.import_url, {"csv_file": csv_file})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Import mislukt" in content
        assert "duplicate email" in content

    def test_import_skips_existing_users(self):
        """Test that import skips users with existing email addresses"""
        self.client.force_login(self.auth_user)
        # Create existing user
        User.objects.create(
            username="existing", email="existing@rijksoverheid.nl", first_name="Existing", last_name="User"
        )

        csv_content = """first_name,last_name,email
John,Doe,john@rijksoverheid.nl
Jane,Smith,existing@rijksoverheid.nl"""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(self.import_url, {"csv_file": csv_file})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Import geslaagd" in content
        assert "1" in content  # Only 1 user created
        assert "already exists" in content

        # Verify only John was created
        assert User.objects.filter(email="john@rijksoverheid.nl").exists()
        assert User.objects.filter(email="existing@rijksoverheid.nl").count() == 1

    def test_import_without_optional_fields(self):
        """Test import with only required fields (no brand, no groups)"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email
John,Doe,john@rijksoverheid.nl"""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(self.import_url, {"csv_file": csv_file})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Import geslaagd" in content

        john = User.objects.get(email="john@rijksoverheid.nl")
        assert john.labels.count() == 0
        assert john.groups.count() == 0

    def test_import_with_multiple_groups(self):
        """Test user assigned to multiple groups"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email,brand,Beheerder,Consultant,BDM
John,Doe,john@rijksoverheid.nl,Brand A,y,y,y"""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(self.import_url, {"csv_file": csv_file})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Import geslaagd" in content

        john = User.objects.get(email="john@rijksoverheid.nl")
        assert john.groups.count() == 3
        assert john.groups.filter(name="Beheerder").exists()
        assert john.groups.filter(name="Consultant").exists()
        assert john.groups.filter(name="Business Development Manager").exists()

    def test_import_empty_csv(self):
        """Test import with empty CSV file"""
        self.client.force_login(self.auth_user)
        csv_content = ""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(self.import_url, {"csv_file": csv_file})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Import mislukt" in content
        assert "empty" in content

    def test_import_csv_with_only_headers(self):
        """Test import with CSV that has headers but no data rows"""
        self.client.force_login(self.auth_user)
        csv_content = "first_name,last_name,email"
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(self.import_url, {"csv_file": csv_file})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Import geslaagd" in content
        assert "0" in content  # 0 users created

    def test_import_validates_all_before_creating(self):
        """Test that validation happens before any users are created"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email
John,Doe,john@rijksoverheid.nl
Jane,Smith,invalid-email"""
        csv_file = self._create_csv_file(csv_content)

        user_count_before = User.objects.count()

        response = self.client.post(self.import_url, {"csv_file": csv_file})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Import mislukt" in content
        # No users should be created if validation fails
        assert User.objects.count() == user_count_before

    def test_import_handles_whitespace_in_fields(self):
        """Test that import properly trims whitespace from fields"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email,brand,Beheerder,Consultant,BDM
  John  ,  Doe  ,  john@rijksoverheid.nl  ,  Brand A  , y , n , n """
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(self.import_url, {"csv_file": csv_file})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Import geslaagd" in content

        john = User.objects.get(email="john@rijksoverheid.nl")
        assert john.first_name == "John"
        assert john.last_name == "Doe"
        assert john.labels.filter(name="Brand A").exists()
