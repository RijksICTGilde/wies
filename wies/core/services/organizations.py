"""Organization sync service.

Syncs organizations from organisaties.overheid.nl XML export.
Supports hierarchical import of ministries with their DG's, directies and afdelingen.
"""

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime

import requests
from django.utils import timezone

from wies.core.models import OrganizationType, OrganizationUnit
from wies.core.services.events import create_event

logger = logging.getLogger(__name__)

ORGANISATIES_OVERHEID_URL = "https://organisaties.overheid.nl/archive/exportOO.xml"
NS = {"p": "https://organisaties.overheid.nl/static/schema/oo/export/2.6.9"}

# Organizations excluded from sync (intelligence services).
# All comparisons are case-insensitive.
EXCLUDED_ORG_NAMES: set[str] = {
    "algemene inlichtingen- en veiligheidsdienst",
    "militaire inlichtingen- en veiligheidsdienst",
}
EXCLUDED_ORG_ABBREVIATIONS: set[str] = {"aivd", "mivd"}


def _is_excluded_org(name: str, abbreviations: list[str]) -> bool:
    """Check if an organization should be excluded from sync."""
    name_lower = name.lower()
    if any(excluded in name_lower for excluded in EXCLUDED_ORG_NAMES):
        return True
    return any(abbr.lower() in EXCLUDED_ORG_ABBREVIATIONS for abbr in abbreviations)


def build_source_url(system_id: str, name: str) -> str:
    """Build URL to organisaties.overheid.nl page."""
    if not system_id:
        return ""
    # Replace spaces and special chars with underscores for URL
    slug = re.sub(r"[^\w\-]", "_", name)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return f"https://organisaties.overheid.nl/{system_id}/{slug}/"


@dataclass
class SyncResult:
    """Result of organization sync."""

    created: int = 0
    updated: int = 0
    unchanged: int = 0
    deactivated: int = 0
    errors: list[str] = field(default_factory=list)

    def __add__(self, other: "SyncResult") -> "SyncResult":
        """Combine two SyncResults."""
        return SyncResult(
            created=self.created + other.created,
            updated=self.updated + other.updated,
            unchanged=self.unchanged + other.unchanged,
            deactivated=self.deactivated + other.deactivated,
            errors=self.errors + other.errors,
        )


def parse_organization_element(
    org_elem: ET.Element,
) -> dict | None:
    """Parse a single organization element from XML.

    Returns dict with organization data, including nested children and is_active flag.
    Returns None only for excluded organizations (e.g. intelligence services).
    """
    name = org_elem.findtext("p:naam", "", NS).strip()
    abbreviations = [a.text.strip() for a in org_elem.findall("p:afkorting", NS) if a.text]

    # Skip excluded organizations (intelligence services) and all their children
    if _is_excluded_org(name, abbreviations):
        return None

    # Determine if organization is inactive based on eindDatum
    is_active = True
    einddatum_elem = org_elem.find("p:eindDatum", NS)
    if einddatum_elem is not None and einddatum_elem.text:
        try:
            einddatum = datetime.fromisoformat(einddatum_elem.text.strip()).date()
            today = timezone.now().date()
            if einddatum < today:
                is_active = False
        except ValueError:
            # Invalid date format, log and continue processing
            logger.warning("Invalid eindDatum format for organization '%s': %s", name, einddatum_elem.text)

    org_type_names = [t.text for t in org_elem.findall("p:types/p:type", NS) if t.text]

    # Get identifiers
    tooi = org_elem.get(f"{{{NS['p']}}}resourceIdentifierTOOI", "")
    system_id = org_elem.get(f"{{{NS['p']}}}systeemId", org_elem.get("systeemId", ""))

    # Initialize label with default value
    label = name
    for organization_type in org_type_names:
        # Add "Ministerie van" prefix if needed (case-insensitive check)
        if organization_type.lower() == "ministerie" and not name.startswith("Ministerie"):
            label = f"Ministerie van {name}"

    # Get related ministry TOOI from relatieMetMinisterie element's attribute
    related_ministry_tooi = ""
    related_ministry_elem = org_elem.find("p:relatieMetMinisterie", NS)
    if related_ministry_elem is not None:
        related_ministry_tooi = related_ministry_elem.get(f"{{{NS['p']}}}resourceIdentifierTOOI", "")

    # Build source URL
    source_url = build_source_url(system_id, name)

    # Parse nested organizations
    children = []
    for child_elem in org_elem.findall("p:organisaties/p:organisatie", NS):
        child_data = parse_organization_element(child_elem)
        if child_data:
            # If parent is inactive, all children are also inactive
            if not is_active:
                child_data["is_active"] = False
            children.append(child_data)

    return {
        "name": name,
        "system_id": system_id,
        "label": label,
        "org_type_names": org_type_names,
        "tooi_identifier": tooi if tooi else None,
        "abbreviations": abbreviations,
        "source_url": source_url if source_url else None,
        "children": children,
        "related_ministry_tooi": related_ministry_tooi,
        "is_active": is_active,
    }


def parse_xml_hierarchical(xml_content: bytes) -> list[dict]:
    """Parse organizations from XML export with hierarchy.

    Args:
        xml_content: Raw XML bytes

    Returns:
        List of organization dicts with nested children
    """
    root = ET.fromstring(xml_content)  # noqa: S314
    organizations = []

    # Find top-level organizations (those with TOOI identifier at root level)
    for org in root.findall("p:organisaties/p:organisatie", NS):
        org_data = parse_organization_element(org)
        if org_data is None:
            continue

        organizations.append(org_data)

    return organizations


def sync_organization_tree(
    org_data: dict,
    parent: OrganizationUnit | None,
    *,
    dry_run: bool,
    seen_ids: set[int] | None = None,
) -> SyncResult:
    """Recursively sync an organization and its children.

    Args:
        org_data: Dict with organization data and children
        parent: Parent OrganizationUnit (None for root)
        dry_run: If True, don't apply changes
        seen_ids: Set to collect IDs of all orgs processed during sync

    Returns:
        SyncResult with counts
    """
    result = SyncResult()
    children = org_data.pop("children", [])
    is_active = org_data.pop("is_active", True)

    # Find existing org by TOOI
    new_tooi = org_data.get("tooi_identifier")
    db_org = None
    if new_tooi:
        db_org = OrganizationUnit.objects.filter(tooi_identifier=new_tooi).first()

    if not db_org:
        # For orgs without TOOI, match by name + parent + types
        candidates = OrganizationUnit.objects.filter(
            name=org_data["name"],
            parent=parent,
        ).prefetch_related("organization_types")

        new_type_names = set(org_data["org_type_names"])

        # Search through all candidates to find one with matching types
        for candidate in candidates:
            # Skip if both have TOOI but they differ (distinct organizations with same name)
            if new_tooi and candidate.tooi_identifier and new_tooi != candidate.tooi_identifier:
                continue
            # Skip if candidate has TOOI but incoming doesn't
            if not new_tooi and candidate.tooi_identifier:
                continue

            db_type_names = set(candidate.organization_types.values_list("name", flat=True))

            # Check if types match
            if not db_type_names or not new_type_names:
                # If either has no types, accept the match (types can be populated/updated)
                db_org = candidate
                break
            if db_type_names == new_type_names:
                # Types match perfectly
                db_org = candidate
                break
            # Otherwise, types differ - keep searching for a better match

    organization_types = []
    if not dry_run:
        for org_type_name in org_data["org_type_names"]:
            organization_type, _ = OrganizationType.objects.get_or_create(
                name=org_type_name, defaults={"label": org_type_name}
            )
            organization_types.append(organization_type)

    try:
        # Separate ManyToMany fields from regular attributes
        m2m_fields = {"organization_types": organization_types}
        new_org_attributes = {
            "name": org_data["name"],
            "label": org_data["label"],
            "abbreviations": org_data["abbreviations"],
            "related_ministry_tooi": org_data["related_ministry_tooi"],
            "parent": parent,
            "tooi_identifier": new_tooi,
            "oin_number": None,
            "system_id": org_data["system_id"],
            "source_url": org_data["source_url"],
            "is_active": is_active,
        }

        if db_org:
            changes = {}
            for attribute, new_value in new_org_attributes.items():
                old_value = getattr(db_org, attribute)
                if old_value != new_value:
                    # Store parent as ID for JSON serialization
                    if attribute == "parent":
                        changes[attribute] = {
                            "old": old_value.id if old_value else None,
                            "new": new_value.id if new_value else None,
                        }
                    else:
                        changes[attribute] = {"old": old_value, "new": new_value}
                if not dry_run:
                    setattr(db_org, attribute, new_value)

            # Check ManyToMany fields separately
            for m2m_field, new_value in m2m_fields.items():
                # Compare by PK sets to avoid order-dependent comparison
                current_pks = set(getattr(db_org, m2m_field).values_list("pk", flat=True))
                new_pks = {obj.pk for obj in new_value}
                if current_pks != new_pks:
                    changes[m2m_field] = {"old": sorted(current_pks), "new": sorted(new_pks)}
                if not dry_run:
                    getattr(db_org, m2m_field).set(new_value)

            if changes:
                if not dry_run:
                    db_org.save()
                    logger.info("Updated: %s", db_org)
                    create_event(
                        "",
                        "OrgSync.update",
                        {
                            "org_id": db_org.id,
                            "tooi": db_org.tooi_identifier or "",
                            "changes": changes,
                        },
                    )
                result.updated += 1
            else:
                result.unchanged += 1

            new_org = db_org
        else:
            # Don't create new records for inactive organizations
            if not is_active:
                logger.debug("Skipping creation of inactive org: %s", org_data["name"])
                # Still recurse children — they may have existing DB records to update
                for child_data in children:
                    child_result = sync_organization_tree(
                        child_data,
                        parent=None,
                        dry_run=dry_run,
                        seen_ids=seen_ids,
                    )
                    result = result + child_result
                return result

            # Create new organization
            # Log why we're creating instead of matching
            if new_tooi:
                logger.info(
                    "Creating (not found by TOOI): %s | TOOI=%s",
                    org_data["name"],
                    new_tooi,
                )
            elif parent:
                logger.info(
                    "Creating (not found by name+parent+type): %s | parent=%s",
                    org_data["name"],
                    parent.name if parent else None,
                )
            else:
                logger.info("Creating (no TOOI, no matching parent+type): %s", org_data["name"])

            if not dry_run:
                new_org = OrganizationUnit.objects.create(**new_org_attributes)
                # Set ManyToMany fields after creation
                for m2m_field, value in m2m_fields.items():
                    getattr(new_org, m2m_field).set(value)
                logger.info("Created: %s", new_org)
                create_event(
                    "",
                    "OrgSync.create",
                    {
                        "org_id": new_org.id,
                        "tooi": new_org.tooi_identifier or "",
                        "name": new_org.name,
                    },
                )
            else:
                new_org = None
            result.created += 1

    except Exception as e:
        error_msg = f"Error processing {org_data.get('name', 'unknown')}: {e}"
        logger.exception(error_msg)
        result.errors.append(error_msg)
        return result

    # Track this org as seen during sync
    if seen_ids is not None and new_org is not None:
        seen_ids.add(new_org.id)

    # Recursively sync children
    for child_data in children:
        child_result = sync_organization_tree(
            child_data,
            parent=db_org if dry_run else new_org,
            dry_run=dry_run,
            seen_ids=seen_ids,
        )
        result = result + child_result

    return result


def sync_organizations(
    *,
    xml_content: bytes | None = None,
    url: str | None = None,
    dry_run: bool = False,
) -> SyncResult:
    """Sync organizations from XML to database.

    Args:
        xml_content: XML bytes (downloads from URL if not provided)
        dry_run: If True, don't apply changes

    Returns:
        SyncResult with counts
    """
    result = SyncResult()

    # Fetch XML if not provided
    if xml_content is None:
        fetch_url = url or ORGANISATIES_OVERHEID_URL
        logger.info("Fetching organizations from %s", fetch_url)

        response = requests.get(fetch_url, timeout=120)
        if response.status_code == 200:  # noqa: PLR2004 (status code is not magic)
            xml_content = response.content
        else:
            logger.error("Unable to get xml content")
            return None

    # Parse XML with hierarchy
    organizations = parse_xml_hierarchical(xml_content)
    logger.info("Parsed %d root organizations from XML", len(organizations))

    # Sync each organization tree
    seen_ids: set[int] = set()
    for org_data in organizations:
        org_result = sync_organization_tree(org_data, parent=None, dry_run=dry_run, seen_ids=seen_ids)
        result = result + org_result

    # Deactivate external orgs not seen during a full sync
    if not dry_run and seen_ids:
        orgs_to_deactivate = list(
            OrganizationUnit.objects.filter(is_active=True)
            .exclude(source_url="")
            .exclude(source_url__isnull=True)
            .exclude(id__in=seen_ids)
            .values_list("id", "tooi_identifier", "name")
        )
        if orgs_to_deactivate:
            OrganizationUnit.objects.filter(id__in=[org[0] for org in orgs_to_deactivate]).update(is_active=False)
            for org_id, tooi, name in orgs_to_deactivate:
                create_event(
                    "",
                    "OrgSync.deactivate",
                    {
                        "org_id": org_id,
                        "tooi": tooi or "",
                        "name": name,
                        "reason": "not_seen_in_sync",
                    },
                )
        result.deactivated = len(orgs_to_deactivate)
        if orgs_to_deactivate:
            logger.info("Deactivated %d external orgs not seen in sync", len(orgs_to_deactivate))

    logger.info(
        "Sync completed: created=%s, updated=%s, unchanged=%s, deactivated=%s",
        result.created,
        result.updated,
        result.unchanged,
        result.deactivated,
    )

    return result


def get_org_descendant_ids(root_ids: list[int]) -> set[int]:
    """Return the set of IDs for the given roots and all their descendants.

    Loads all OrganizationUnits once and traverses the tree in Python to avoid
    recursive SQL — SQLite-friendly and fast for typical government org trees.
    """
    all_orgs = OrganizationUnit.objects.values_list("id", "parent_id")
    children_map: dict[int, list[int]] = {}
    for org_id, parent_id in all_orgs:
        if parent_id is not None:
            children_map.setdefault(parent_id, []).append(org_id)

    result: set[int] = set()
    queue = list(root_ids)
    while queue:
        current = queue.pop()
        result.add(current)
        queue.extend(children_map.get(current, []))
    return result
