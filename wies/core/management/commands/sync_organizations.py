"""Sync organizations from organisaties.overheid.nl.

Usage:
    python manage.py sync_organizations              # Preview + confirm
    python manage.py sync_organizations --yes        # Apply without confirm
    python manage.py sync_organizations --dry-run    # Preview only
    python manage.py sync_organizations --type Ministerie
"""

from pathlib import Path

from django.core.management.base import BaseCommand

from wies.core.services.sync_organizations import sync_organizations


class Command(BaseCommand):
    help = "Sync organizations from organisaties.overheid.nl"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without applying",
        )
        parser.add_argument(
            "--yes",
            "-y",
            action="store_true",
            help="Apply changes without confirmation prompt",
        )
        parser.add_argument(
            "--file",
            type=Path,
            help="Use local XML file (for CI/CD without internet)",
        )
        parser.add_argument(
            "--type",
            dest="filter_type",
            help="Only sync specific type (e.g., Ministerie)",
        )

    def handle(self, *args, **options):
        dry_run_only = options["dry_run"]
        skip_confirm = options["yes"]
        file_path = options.get("file")
        filter_type = options.get("filter_type")

        # Load XML from file if provided
        xml_content = None
        if file_path:
            if not file_path.exists():
                self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
                return
            xml_content = file_path.read_bytes()

        # First do a dry run to show what would happen
        try:
            result = sync_organizations(
                xml_content=xml_content,
                filter_type=filter_type,
                dry_run=True,
            )
        except TimeoutError:
            self.stdout.write(self.style.ERROR("Timeout - use --file with local XML"))
            return

        # Show results
        self.stdout.write("\nChanges:")
        self.stdout.write(f"  Create: {result.created}")
        self.stdout.write(f"  Update: {result.updated}")
        self.stdout.write(f"  Unchanged: {result.unchanged}")

        if result.errors:
            self.stdout.write(self.style.ERROR(f"  Errors: {len(result.errors)}"))
            for error in result.errors:
                self.stdout.write(self.style.ERROR(f"    - {error}"))

        # If dry-run only, stop here
        if dry_run_only:
            self.stdout.write(self.style.WARNING("\nDry run - no changes applied."))
            return

        # If nothing to do, stop here
        if result.created == 0 and result.updated == 0:
            self.stdout.write(self.style.SUCCESS("\nNo changes needed."))
            return

        # Confirm before applying
        if not skip_confirm:
            confirm = input("\nApply these changes? [y/N] ")
            if confirm.lower() not in ("y", "yes"):
                self.stdout.write("Cancelled.")
                return

        # Apply changes
        result = sync_organizations(
            xml_content=xml_content,
            filter_type=filter_type,
            dry_run=False,
        )

        self.stdout.write(self.style.SUCCESS(f"\nApplied: {result.created} created, {result.updated} updated."))
