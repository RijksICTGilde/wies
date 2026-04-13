"""Migrate data from old env (productie) JSON dump to new env (production).

Handles schema differences:
- core.user → rijksauth.user (drop username, key by email)
- core.event → split: auth events skipped, core events skipped (per decision)
- FK remapping via old_pk → new_pk mappings
- Merge strategy: match by name/email, don't clear existing data

Usage:
    python manage.py migrate_old_data path/to/wies_datadump.json
"""

import json
import logging
from collections import defaultdict
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    Label,
    LabelCategory,
    OrganizationType,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
)

logger = logging.getLogger(__name__)
User = get_user_model()

MODELS_TO_IMPORT = {
    "core.user",
    "core.labelcategory",
    "core.label",
    "core.skill",
    "core.colleague",
    "core.organizationtype",
    "core.organizationunit",
    "core.assignment",
    "core.assignmentorganizationunit",
    "core.service",
    "core.placement",
}


def _group_by_model(records: list[dict]) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for record in records:
        grouped[record["model"]].append(record)
    return grouped


def _build_uuid_to_email(user_records: list[dict]) -> dict[str, str]:
    """Map old user UUID usernames to email addresses."""
    mapping = {}
    for record in user_records:
        username = record["fields"].get("username", "")
        email = record["fields"]["email"]
        if username:
            mapping[username] = email
    return mapping


class Command(BaseCommand):
    help = "Migrate data from old env JSON dump to new env with schema remapping"

    def add_arguments(self, parser):
        parser.add_argument("json_file", type=str, help="Path to the old env JSON dump file")

    @transaction.atomic
    def handle(self, *args, **options):
        json_path = Path(options["json_file"])
        if not json_path.exists():
            self.stderr.write(f"File not found: {json_path}")
            return

        self.stdout.write(f"Loading {json_path}...")
        records = json.loads(json_path.read_text())
        grouped = _group_by_model(records)

        self.stdout.write(f"Total records: {len(records)}")
        for model, recs in sorted(grouped.items()):
            self.stdout.write(f"  {model}: {len(recs)}")

        # Build UUID→email mapping from old users
        uuid_to_email = _build_uuid_to_email(grouped.get("core.user", []))

        # Process in dependency order
        stats = {}
        stats["users"] = self._import_users(grouped.get("core.user", []))
        stats["label_categories"] = self._import_label_categories(grouped.get("core.labelcategory", []))
        label_pk_map = stats["label_categories"]["cat_pk_map"]
        stats["labels"] = self._import_labels(grouped.get("core.label", []), label_pk_map)
        stats["skills"] = self._import_skills(grouped.get("core.skill", []))
        stats["org_types"] = self._import_org_types(grouped.get("core.organizationtype", []))
        stats["org_units"] = self._import_org_units(
            grouped.get("core.organizationunit", []),
            stats["org_types"]["pk_map"],
        )
        stats["colleagues"] = self._import_colleagues(
            grouped.get("core.colleague", []),
            uuid_to_email,
            stats["labels"]["pk_map"],
            stats["skills"]["pk_map"],
        )
        stats["assignments"] = self._import_assignments(
            grouped.get("core.assignment", []),
            stats["colleagues"]["pk_map"],
        )
        stats["assignment_org_units"] = self._import_assignment_org_units(
            grouped.get("core.assignmentorganizationunit", []),
            stats["assignments"]["pk_map"],
            stats["org_units"]["pk_map"],
        )
        stats["services"] = self._import_services(
            grouped.get("core.service", []),
            stats["assignments"]["pk_map"],
            stats["skills"]["pk_map"],
        )
        stats["placements"] = self._import_placements(
            grouped.get("core.placement", []),
            stats["colleagues"]["pk_map"],
            stats["services"]["pk_map"],
        )

        self.stdout.write("\n=== Migration Summary ===")
        for name, stat in stats.items():
            created = stat.get("created", 0)
            updated = stat.get("updated", 0)
            skipped = stat.get("skipped", 0)
            self.stdout.write(f"  {name}: created={created}, updated={updated}, skipped={skipped}")

        self.stdout.write(self.style.SUCCESS("Migration complete!"))

    def _import_users(self, records: list[dict]) -> dict:
        created = updated = 0
        for record in records:
            fields = record["fields"]
            email = fields["email"]
            defaults = {
                "is_superuser": fields["is_superuser"],
                "first_name": fields.get("first_name", ""),
                "last_name": fields.get("last_name", ""),
                "is_staff": fields["is_staff"],
                "is_active": fields["is_active"],
            }
            _, was_created = User.objects.update_or_create(email=email, defaults=defaults)
            if was_created:
                created += 1
            else:
                updated += 1
        return {"created": created, "updated": updated, "skipped": 0}

    def _import_label_categories(self, records: list[dict]) -> dict:
        created = updated = 0
        cat_pk_map = {}  # old_pk → new_pk
        for record in records:
            old_pk = record["pk"]
            fields = record["fields"]
            cat, was_created = LabelCategory.objects.update_or_create(
                name=fields["name"],
                defaults={"color": fields["color"]},
            )
            cat_pk_map[old_pk] = cat.pk
            if was_created:
                created += 1
            else:
                updated += 1
        return {"created": created, "updated": updated, "skipped": 0, "cat_pk_map": cat_pk_map}

    def _import_labels(self, records: list[dict], cat_pk_map: dict[int, int]) -> dict:
        created = skipped = 0
        pk_map = {}  # old_pk → new_pk
        for record in records:
            old_pk = record["pk"]
            fields = record["fields"]
            old_cat_pk = fields["category"]
            new_cat_pk = cat_pk_map.get(old_cat_pk)
            if new_cat_pk is None:
                skipped += 1
                continue
            label, was_created = Label.objects.get_or_create(
                name=fields["name"],
                category_id=new_cat_pk,
            )
            pk_map[old_pk] = label.pk
            if was_created:
                created += 1
        return {"created": created, "updated": 0, "skipped": skipped, "pk_map": pk_map}

    def _import_skills(self, records: list[dict]) -> dict:
        created = 0
        pk_map = {}
        for record in records:
            old_pk = record["pk"]
            skill, was_created = Skill.objects.get_or_create(name=record["fields"]["name"])
            pk_map[old_pk] = skill.pk
            if was_created:
                created += 1
        return {"created": created, "updated": 0, "skipped": 0, "pk_map": pk_map}

    def _import_org_types(self, records: list[dict]) -> dict:
        created = 0
        pk_map = {}
        for record in records:
            old_pk = record["pk"]
            fields = record["fields"]
            org_type, was_created = OrganizationType.objects.get_or_create(
                name=fields["name"],
                defaults={"label": fields["label"]},
            )
            pk_map[old_pk] = org_type.pk
            if was_created:
                created += 1
        return {"created": created, "updated": 0, "skipped": 0, "pk_map": pk_map}

    def _org_unit_fields(self, fields: dict, parent_id: int | None) -> dict:
        """Build field dict for an OrganizationUnit from dump fields."""
        return {
            "name": fields["name"],
            "label": fields.get("label", ""),
            "abbreviations": fields.get("abbreviations", []),
            "related_ministry_tooi": fields.get("related_ministry_tooi", ""),
            "parent_id": parent_id,
            "tooi_identifier": fields.get("tooi_identifier") or None,
            "oin_number": fields.get("oin_number") or None,
            "system_id": fields.get("system_id", ""),
            "source_url": fields.get("source_url", ""),
            "end_date": fields.get("end_date"),
        }

    def _import_org_units(self, records: list[dict], org_type_pk_map: dict[int, int]) -> dict:
        created = updated = 0
        pk_map = {}

        # Build lookup for topological ordering: process parents before children
        records_by_old_pk = {r["pk"]: r for r in records}

        def get_order(record):
            """Return depth in parent chain for topological sorting."""
            depth = 0
            current = record
            visited = set()
            while current["fields"]["parent"] is not None:
                parent_pk = current["fields"]["parent"]
                if parent_pk in visited:
                    break
                visited.add(parent_pk)
                current = records_by_old_pk.get(parent_pk)
                if current is None:
                    break
                depth += 1
            return depth

        sorted_records = sorted(records, key=get_order)

        for record in sorted_records:
            old_pk = record["pk"]
            fields = record["fields"]
            parent_id = pk_map.get(fields["parent"]) if fields["parent"] is not None else None

            # Match by tooi_identifier if available (unique), otherwise always create
            # because names like "Provinciale Staten" appear multiple times
            org_unit = None
            if fields.get("tooi_identifier"):
                org_unit = OrganizationUnit.objects.filter(tooi_identifier=fields["tooi_identifier"]).first()

            if org_unit:
                for attr, value in self._org_unit_fields(fields, parent_id).items():
                    setattr(org_unit, attr, value)
                org_unit.save()
                updated += 1
            else:
                org_unit = OrganizationUnit.objects.create(**self._org_unit_fields(fields, parent_id))
                created += 1

            # Set M2M organization_types
            if fields.get("organization_types"):
                new_type_pks = [
                    org_type_pk_map[old_type_pk]
                    for old_type_pk in fields["organization_types"]
                    if old_type_pk in org_type_pk_map
                ]
                org_unit.organization_types.set(new_type_pks)

            pk_map[old_pk] = org_unit.pk

        return {"created": created, "updated": updated, "skipped": 0, "pk_map": pk_map}

    def _import_colleagues(
        self,
        records: list[dict],
        uuid_to_email: dict[str, str],
        label_pk_map: dict[int, int],
        skill_pk_map: dict[int, int],
    ) -> dict:
        created = updated = 0
        pk_map = {}

        for record in records:
            old_pk = record["pk"]
            fields = record["fields"]

            # Resolve user FK: old dump has [uuid] natural key → map to email → find user
            user = None
            if fields.get("user"):
                uuid = fields["user"][0]  # natural key is [username]
                email = uuid_to_email.get(uuid)
                if email:
                    user = User.objects.filter(email=email).first()

            defaults = {
                "name": fields["name"],
                "user": user,
            }

            colleague, was_created = Colleague.objects.update_or_create(
                email=fields["email"],
                source=fields["source"],
                defaults=defaults,
            )

            # Set M2M labels
            if fields.get("labels"):
                new_label_pks = [label_pk_map[old_pk_l] for old_pk_l in fields["labels"] if old_pk_l in label_pk_map]
                colleague.labels.set(new_label_pks)

            # Set M2M skills
            if fields.get("skills"):
                new_skill_pks = [skill_pk_map[old_pk_s] for old_pk_s in fields["skills"] if old_pk_s in skill_pk_map]
                colleague.skills.set(new_skill_pks)

            pk_map[old_pk] = colleague.pk
            if was_created:
                created += 1
            else:
                updated += 1

        return {"created": created, "updated": updated, "skipped": 0, "pk_map": pk_map}

    def _import_assignments(self, records: list[dict], colleague_pk_map: dict[int, int]) -> dict:
        created = 0
        pk_map = {}

        for record in records:
            old_pk = record["pk"]
            fields = record["fields"]

            # Remap owner FK
            owner_id = None
            if fields.get("owner"):
                owner_id = colleague_pk_map.get(fields["owner"])

            assignment = Assignment.objects.create(
                name=fields["name"],
                start_date=fields.get("start_date"),
                end_date=fields.get("end_date"),
                owner_id=owner_id,
                extra_info=fields.get("extra_info", ""),
                source=fields["source"],
                source_id=fields.get("source_id", ""),
                source_url=fields.get("source_url", ""),
            )
            pk_map[old_pk] = assignment.pk
            created += 1

        return {"created": created, "updated": 0, "skipped": 0, "pk_map": pk_map}

    def _import_assignment_org_units(
        self,
        records: list[dict],
        assignment_pk_map: dict[int, int],
        org_unit_pk_map: dict[int, int],
    ) -> dict:
        created = skipped = 0

        for record in records:
            fields = record["fields"]
            new_assignment_pk = assignment_pk_map.get(fields["assignment"])
            new_org_pk = org_unit_pk_map.get(fields["organization"])

            if new_assignment_pk is None or new_org_pk is None:
                skipped += 1
                continue

            AssignmentOrganizationUnit.objects.create(
                assignment_id=new_assignment_pk,
                organization_id=new_org_pk,
                role=fields["role"],
            )
            created += 1

        return {"created": created, "updated": 0, "skipped": skipped}

    def _import_services(
        self,
        records: list[dict],
        assignment_pk_map: dict[int, int],
        skill_pk_map: dict[int, int],
    ) -> dict:
        created = skipped = 0
        pk_map = {}

        for record in records:
            old_pk = record["pk"]
            fields = record["fields"]

            new_assignment_pk = assignment_pk_map.get(fields["assignment"])
            if new_assignment_pk is None:
                skipped += 1
                continue

            skill_id = None
            if fields.get("skill"):
                skill_id = skill_pk_map.get(fields["skill"])

            service = Service.objects.create(
                assignment_id=new_assignment_pk,
                description=fields.get("description", ""),
                skill_id=skill_id,
                period_source=fields.get("period_source", "ASSIGNMENT"),
                specific_start_date=fields.get("specific_start_date"),
                specific_end_date=fields.get("specific_end_date"),
                status=fields.get("status", "OPEN"),
                source=fields["source"],
                source_id=fields.get("source_id", ""),
                source_url=fields.get("source_url", ""),
            )
            pk_map[old_pk] = service.pk
            created += 1

        return {"created": created, "updated": 0, "skipped": skipped, "pk_map": pk_map}

    def _import_placements(
        self,
        records: list[dict],
        colleague_pk_map: dict[int, int],
        service_pk_map: dict[int, int],
    ) -> dict:
        created = skipped = 0

        for record in records:
            fields = record["fields"]

            new_colleague_pk = colleague_pk_map.get(fields["colleague"])
            new_service_pk = service_pk_map.get(fields["service"])

            if new_colleague_pk is None or new_service_pk is None:
                skipped += 1
                continue

            Placement.objects.create(
                colleague_id=new_colleague_pk,
                service_id=new_service_pk,
                period_source=fields.get("period_source", "SERVICE"),
                specific_start_date=fields.get("specific_start_date"),
                specific_end_date=fields.get("specific_end_date"),
                source=fields["source"],
                source_id=fields.get("source_id", ""),
                source_url=fields.get("source_url", ""),
            )
            created += 1

        return {"created": created, "updated": 0, "skipped": skipped}
