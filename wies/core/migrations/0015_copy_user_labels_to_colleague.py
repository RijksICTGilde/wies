"""Data migration: copy labels from User to linked Colleague, then remove User.labels."""

from django.db import migrations


def ensure_colleagues_and_copy_labels(apps, schema_editor):
    """Ensure every User has a Colleague, then copy User labels to it."""
    User = apps.get_model("core", "User")
    Colleague = apps.get_model("core", "Colleague")

    # Step 1: Create a Colleague for every User that doesn't have one
    for user in User.objects.filter(colleague__isnull=True):
        Colleague.objects.create(
            user=user,
            name=f"{user.first_name} {user.last_name}",
            email=user.email,
            source="wies",
        )

    # Step 2: Copy labels from User to linked Colleague
    for user in User.objects.prefetch_related("labels").filter(labels__isnull=False).distinct():
        colleague = user.colleague
        existing_label_ids = set(colleague.labels.values_list("id", flat=True))
        for label in user.labels.all():
            if label.id not in existing_label_ids:
                colleague.labels.add(label)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0014_remove_assignment_status_service_status"),
    ]

    operations = [
        migrations.RunPython(ensure_colleagues_and_copy_labels, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="user",
            name="labels",
        ),
    ]
