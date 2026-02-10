"""Organization sync service.

Syncs organizations from organisaties.overheid.nl XML export.
Supports hierarchical import of ministries with their DG's, directies and afdelingen.
"""

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from urllib.request import urlopen

from wies.core.models import OrganizationType, OrganizationUnit

logger = logging.getLogger(__name__)

ORGANISATIES_OVERHEID_URL = "https://organisaties.overheid.nl/archive/exportOO.xml"
NS = {"p": "https://organisaties.overheid.nl/static/schema/oo/export/2.6.9"}


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
    errors: list[str] = field(default_factory=list)

    def __add__(self, other: "SyncResult") -> "SyncResult":
        """Combine two SyncResults."""
        return SyncResult(
            created=self.created + other.created,
            updated=self.updated + other.updated,
            unchanged=self.unchanged + other.unchanged,
            errors=self.errors + other.errors,
        )


def parse_organization_element(
    org_elem: ET.Element,
) -> dict:
    """Parse a single organization element from XML.

    Returns dict with organization data, including nested children.
    """
    name = org_elem.findtext("p:naam", "", NS).strip()
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

    # Get abbreviations
    abbreviations = [a.text.strip() for a in org_elem.findall("p:afkorting", NS) if a.text]

    # Build source URL
    source_url = build_source_url(system_id, name)

    # Parse nested organizations
    children = []
    for child_elem in org_elem.findall("p:organisaties/p:organisatie", NS):
        child_data = parse_organization_element(child_elem)
        if child_data:
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
    }


def parse_xml_hierarchical(xml_content: bytes, filter_types: list[str] | None = None) -> list[dict]:
    """Parse organizations from XML export with hierarchy.

    Args:
        xml_content: Raw XML bytes
        filter_types: Optional list of root types to include (e.g., ["ministerie"])

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

        # Filter by type if specified
        # Check if any of the organization's types match the filter
        if filter_types and not any(org_type in filter_types for org_type in org_data["org_type_names"]):
            continue

        organizations.append(org_data)

    return organizations


def sync_organization_tree(
    org_data: dict,
    parent: OrganizationUnit | None,
    *,
    dry_run: bool,
) -> SyncResult:
    """Recursively sync an organization and its children.

    Args:
        org_data: Dict with organization data and children
        parent: Parent OrganizationUnit (None for root)
        dry_run: If True, don't apply changes

    Returns:
        SyncResult with counts
    """
    result = SyncResult()
    children = org_data.pop("children", [])

    # Find existing org by TOOI
    new_tooi = org_data.get("tooi_identifier")
    db_org = None
    if new_tooi:
        db_org = OrganizationUnit.objects.filter(tooi_identifier=new_tooi).first()

    if not db_org and parent:
        # For nested orgs without TOOI, match by name + parent

        db_org = OrganizationUnit.objects.filter(
            name=org_data["name"],
            parent=parent,
        ).first()

        if db_org and not new_tooi and db_org.tooi_identifier:
            # if db org has tooi, new org does not have tooi
            # reject db org, since it's probably not the same one
            db_org = None
            # TODO: write test for this

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
        }

        if db_org:
            has_changes = False
            for attribute, new_value in new_org_attributes.items():
                if getattr(db_org, attribute) != new_value:
                    has_changes = True
                if not dry_run:
                    setattr(db_org, attribute, new_value)

            # Check ManyToMany fields separately
            for m2m_field, new_value in m2m_fields.items():
                current_value = list(getattr(db_org, m2m_field).all())
                if current_value != new_value:
                    has_changes = True
                if not dry_run:
                    getattr(db_org, m2m_field).set(new_value)

            if has_changes:
                if not dry_run:
                    db_org.save()
                    logger.info("Updated: %s", db_org)
                result.updated += 1
            else:
                result.unchanged += 1

            new_org = db_org
        else:
            # Create new organization
            if not dry_run:
                new_org = OrganizationUnit.objects.create(**new_org_attributes)
                # Set ManyToMany fields after creation
                for m2m_field, value in m2m_fields.items():
                    getattr(new_org, m2m_field).set(value)
                logger.info("Created: %s", new_org)
            else:
                new_org = None
            result.created += 1

    except Exception as e:
        error_msg = f"Error processing {org_data.get('name', 'unknown')}: {e}"
        logger.exception(error_msg)
        result.errors.append(error_msg)
        return result

    # Recursively sync children
    for child_data in children:
        child_result = sync_organization_tree(
            child_data,
            parent=db_org if dry_run else new_org,
            dry_run=dry_run,
        )
        result = result + child_result

    return result


def sync_organizations(
    *,
    xml_content: bytes | None = None,
    filter_type: str | None = None,
    dry_run: bool = False,
) -> SyncResult:
    """Sync organizations from XML to database.

    Args:
        xml_content: XML bytes (downloads from URL if not provided)
        filter_type: Only sync this XML type (e.g., "Ministerie")
        dry_run: If True, don't apply changes

    Returns:
        SyncResult with counts
    """
    result = SyncResult()

    # Fetch XML if not provided
    if xml_content is None:
        logger.info("Fetching organizations from %s", ORGANISATIES_OVERHEID_URL)
        with urlopen(ORGANISATIES_OVERHEID_URL, timeout=120) as response:  # noqa: S310
            xml_content = response.read()

    # Determine which types to sync
    filter_types = None
    if filter_type:
        filter_types = [filter_type]
    # TODO: seems superfluous / weird

    # Parse XML with hierarchy
    organizations = parse_xml_hierarchical(xml_content, filter_types)
    logger.info("Parsed %d root organizations from XML", len(organizations))

    # Sync each organization tree
    for org_data in organizations:
        org_result = sync_organization_tree(org_data, parent=None, dry_run=dry_run)
        result = result + org_result

    return result
