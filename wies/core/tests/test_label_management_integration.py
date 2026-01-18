from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import Permission

from wies.core.models import User, LabelCategory, Label, Colleague


@override_settings(
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
class LabelManagementIntegrationTest(TestCase):
    """High-level integration tests for complete label lifecycle"""

    def setUp(self):
        """Create test data"""
        self.client = Client()

        # Create admin user with all label permissions
        self.admin_user = User.objects.create(
            username="admin",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
        )

        # Grant all label permissions
        label_cat_permissions = Permission.objects.filter(
            codename__in=['view_labelcategory', 'add_labelcategory', 'change_labelcategory', 'delete_labelcategory']
        )
        label_permissions = Permission.objects.filter(
            codename__in=['view_label', 'add_label', 'change_label', 'delete_label']
        )
        user_permissions = Permission.objects.filter(
            codename__in=['view_user', 'add_user', 'change_user', 'delete_user']
        )
        self.admin_user.user_permissions.add(*label_cat_permissions, *label_permissions, *user_permissions)

        # Create unprivileged user
        self.regular_user = User.objects.create(
            username="regular",
            email="regular@example.com",
            first_name="Regular",
            last_name="User",
        )

    def test_complete_label_lifecycle(self):
        """Test: Create category → Create label → Assign to user → Verify in list → Delete"""
        self.client.force_login(self.admin_user)

        # Step 1: Create a label category
        response = self.client.post(
            reverse('label-category-create'),
            {'name': 'Test Category', 'color': '#F9DFDD', 'display_order': 10},
        )
        self.assertEqual(response.status_code, 200)

        category = LabelCategory.objects.get(name='Test Category')
        self.assertEqual(category.color, '#F9DFDD')

        # Step 2: Create a label in that category
        response = self.client.post(
            f'/instellingen/labels/categorie/{category.id}/labels/aanmaken/',
            {'name': 'Test Label'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        label = Label.objects.get(name='Test Label', category=category)

        # Step 3: Create a user with that label
        response = self.client.post(
            reverse('user-create'),
            {
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'category_Test Category': label.id,
            },
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        user = User.objects.get(email='test@example.com')
        self.assertIn(label, user.labels.all())

        # Step 4: Verify label appears in user list view
        response = self.client.get(reverse('admin-users'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Label')

        # Step 5: Delete the category (should cascade to label and remove from user)
        response = self.client.post(
            reverse('label-category-delete', kwargs={'pk': category.id}),
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        # Verify category and label are deleted
        self.assertFalse(LabelCategory.objects.filter(id=category.id).exists())
        self.assertFalse(Label.objects.filter(id=label.id).exists())

        # Verify user still exists but has no labels
        user.refresh_from_db()
        self.assertEqual(user.labels.count(), 0)

    def test_label_edit_propagates_correctly(self):
        """Test: Editing a label name propagates to all assigned users/colleagues"""
        self.client.force_login(self.admin_user)

        # Create category and label
        category = LabelCategory.objects.create(name='Brands', color='#0066CC')
        label = Label.objects.create(name='Original Name', category=category)

        # Assign to user and colleague
        user = User.objects.create(
            username='test_user',
            email='user@test.com',
            first_name='Test',
            last_name='User'
        )
        user.labels.add(label)

        colleague = Colleague.objects.create(
            name='Test Colleague',
            email='colleague@test.com',
            source='wies'
        )
        colleague.labels.add(label)

        # Edit the label
        response = self.client.post(
            reverse('label-edit', kwargs={'pk': label.id}),
            {'name': 'Updated Name', 'category': category.id},
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        # Verify the label name changed
        label.refresh_from_db()
        self.assertEqual(label.name, 'Updated Name')

        # Verify user and colleague still have the label
        self.assertIn(label, user.labels.all())
        self.assertIn(label, colleague.labels.all())

    def test_permission_boundaries_enforced(self):
        """Test: Users without permissions cannot access label management"""
        self.client.force_login(self.regular_user)

        # Attempt to view label list
        response = self.client.get(reverse('label-admin'))
        self.assertEqual(response.status_code, 403)

        # Attempt to create category
        response = self.client.post(
            reverse('label-category-create'),
            {'name': 'Unauthorized', 'color': '#000000'}
        )
        self.assertEqual(response.status_code, 403)

        # Create a category as admin first
        category = LabelCategory.objects.create(name='Test', color='#111111')

        # Attempt to delete as regular user
        response = self.client.post(
            reverse('label-category-delete', kwargs={'pk': category.id})
        )
        self.assertEqual(response.status_code, 403)

        # Verify category still exists
        self.assertTrue(LabelCategory.objects.filter(id=category.id).exists())

    def test_category_cascade_delete_removes_labels(self):
        """Test: Deleting a category removes all its labels and unassigns from users"""
        self.client.force_login(self.admin_user)

        # Create category with multiple labels
        category = LabelCategory.objects.create(name='Skills', color='#00AA00')
        label1 = Label.objects.create(name='Python', category=category)
        label2 = Label.objects.create(name='Django', category=category)
        label3 = Label.objects.create(name='JavaScript', category=category)

        # Assign labels to users
        user1 = User.objects.create(username='user1', email='user1@test.com', first_name='User', last_name='One')
        user1.labels.add(label1, label2)

        user2 = User.objects.create(username='user2', email='user2@test.com', first_name='User', last_name='Two')
        user2.labels.add(label2, label3)

        # Delete the category
        response = self.client.post(
            reverse('label-category-delete', kwargs={'pk': category.id}),
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        # Verify all labels are deleted
        self.assertFalse(Label.objects.filter(category=category).exists())

        # Verify users still exist but have no labels
        user1.refresh_from_db()
        user2.refresh_from_db()
        self.assertEqual(user1.labels.count(), 0)
        self.assertEqual(user2.labels.count(), 0)

    def test_duplicate_label_name_in_same_category_prevented(self):
        """Test: Cannot create duplicate label names within the same category"""
        self.client.force_login(self.admin_user)

        # Create category and label
        category = LabelCategory.objects.create(name='Test Category', color='#AABBCC')
        Label.objects.create(name='Duplicate Name', category=category)

        # Attempt to create another label with same name in same category
        response = self.client.post(
            f'/instellingen/labels/categorie/{category.id}/labels/aanmaken/',
            {'name': 'Duplicate Name'}
        )

        # Should show error or validation failure
        # The exact status depends on form validation - could be 200 with error message
        # or redirect, but duplicate should not be created
        duplicate_count = Label.objects.filter(name='Duplicate Name', category=category).count()
        self.assertEqual(duplicate_count, 1, "Duplicate label was created when it should have been prevented")

    def test_same_label_name_in_different_categories_allowed(self):
        """Test: Can create labels with same name in different categories"""
        self.client.force_login(self.admin_user)

        # Create two categories
        category1 = LabelCategory.objects.create(name='Category 1', color='#111111')
        category2 = LabelCategory.objects.create(name='Category 2', color='#222222')

        # Create label with same name in both categories
        response1 = self.client.post(
            f'/instellingen/labels/categorie/{category1.id}/labels/aanmaken/',
            {'name': 'Common Name'},
        )

        self.assertEqual(response1.status_code, 200)

        response2 = self.client.post(
            f'/instellingen/labels/categorie/{category2.id}/labels/aanmaken/',
            {'name': 'Common Name'},
            follow=True
        )
        self.assertEqual(response2.status_code, 200)

        # Verify both labels exist
        self.assertTrue(Label.objects.filter(name='Common Name', category=category1).exists())
        self.assertTrue(Label.objects.filter(name='Common Name', category=category2).exists())
        self.assertEqual(Label.objects.filter(name='Common Name').count(), 2)

    def test_navigation_menu_visibility(self):
        """Test: Beheer menu only visible to users with appropriate permissions"""
        # Regular user without permissions
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse('placements'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Instellingen')

        # Admin user with permissions
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('placements'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Instellingen')
