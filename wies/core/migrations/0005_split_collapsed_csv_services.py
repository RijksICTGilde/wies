from django.db import migrations, models


def split_collapsed_services(apps, schema_editor):
    """
    For every CSV-sourced Service with >1 Placement, keep the highest-id
    Placement on the original Service (the one currently visible in the team
    panel — preserves any per-Service description/status already set in
    production) and move every surplus Placement onto its own cloned Service.

    Only operates on source="wies". OTYS-sourced services genuinely model
    N candidates per vacancy upstream and must not be touched.
    """
    Service = apps.get_model("core", "Service")
    affected_ids = list(
        Service.objects.filter(source="wies")
        .annotate(n=models.Count("placements"))
        .filter(n__gt=1)
        .values_list("id", flat=True)
    )
    for svc_id in affected_ids:
        svc = Service.objects.get(id=svc_id)
        placements = list(svc.placements.order_by("id"))
        surplus = placements[:-1]
        for p in surplus:
            new_svc = Service.objects.create(
                assignment_id=svc.assignment_id,
                description=svc.description,
                skill_id=svc.skill_id,
                period_source=svc.period_source,
                specific_start_date=svc.specific_start_date,
                specific_end_date=svc.specific_end_date,
                status=svc.status,
                source=svc.source,
                source_url=svc.source_url,
            )
            p.service_id = new_svc.id
            p.save(update_fields=["service"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_alter_colleague_email_constraint"),
    ]

    operations = [
        migrations.RunPython(split_collapsed_services, migrations.RunPython.noop),
    ]
