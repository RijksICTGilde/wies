from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase

from wies.core.models import Label, LabelCategory


class SetupCommandTest(TestCase):
    def test_setup_creates_roles(self):
        call_command("setup")

        assert Group.objects.filter(name="Beheerder").exists()
        assert Group.objects.filter(name="Consultant").exists()
        assert Group.objects.filter(name="Business Development Manager").exists()

    def test_setup_creates_label_categories_and_labels(self):
        call_command("setup")

        assert LabelCategory.objects.count() > 0
        assert Label.objects.count() > 0

    def test_setup_is_idempotent(self):
        call_command("setup")
        initial_category_count = LabelCategory.objects.count()
        initial_label_count = Label.objects.count()
        initial_group_count = Group.objects.count()

        call_command("setup")

        assert LabelCategory.objects.count() == initial_category_count
        assert Label.objects.count() == initial_label_count
        assert Group.objects.count() == initial_group_count
