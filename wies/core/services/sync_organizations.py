"""Organization sync service.

Syncs organizations from organisaties.overheid.nl XML export.
"""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.request import urlopen

from wies.core.models import XML_TYPE_MAPPING, OrganizationUnit

logger = logging.getLogger(__name__)

ORGANISATIES_OVERHEID_URL = "https://organisaties.overheid.nl/archive/exportOO.xml"
NS = {"p": "https://organisaties.overheid.nl/static/schema/oo/export/2.6.9"}


@dataclass
class SyncResult:
    """Result of organization sync."""

    created: int = 0
    updated: int = 0
    unchanged: int = 0
    errors: list[str] | None = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def parse_xml(xml_content: bytes) -> list[dict]:
    """Parse organizations from XML export."""
    root = ET.fromstring(xml_content)  # noqa: S314
    organizations = []

    for org in root.findall(".//p:organisatie", NS):
        types = [t.text for t in org.findall(".//p:types/p:type", NS) if t.text]

        our_type = None
        for xml_type in types:
            if xml_type in XML_TYPE_MAPPING:
                our_type = XML_TYPE_MAPPING[xml_type]
                break

        if our_type is None:
            continue

        naam = org.findtext("p:naam", "", NS).strip()
        tooi = org.get(f"{{{NS['p']}}}resourceIdentifierTOOI", "")

        if not naam or not tooi:
            continue

        if our_type == "ministerie" and not naam.startswith("Ministerie"):
            naam = f"Ministerie van {naam}"

        abbreviations = [a.text.strip() for a in org.findall("p:afkorting", NS) if a.text]

        organizations.append(
            {
                "name": naam,
                "organization_type": our_type,
                "tooi_identifier": tooi,
                "abbreviations": abbreviations,
            }
        )

    return organizations


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
        with urlopen(ORGANISATIES_OVERHEID_URL, timeout=60) as response:  # noqa: S310
            xml_content = response.read()

    organizations = parse_xml(xml_content)
    logger.info("Parsed %d organizations from XML", len(organizations))

    # Filter by type
    if filter_type:
        our_type = XML_TYPE_MAPPING.get(filter_type)
        if our_type:
            organizations = [o for o in organizations if o["organization_type"] == our_type]
        else:
            result.errors.append(f"Unknown type: {filter_type}")
            return result

    # Sync each organization
    for org_data in organizations:
        tooi = org_data.pop("tooi_identifier")
        try:
            existing = OrganizationUnit.objects.filter(tooi_identifier=tooi).first()

            if existing:
                # Check if any field actually changed
                has_changes = any(getattr(existing, k) != v for k, v in org_data.items())
                if has_changes:
                    if not dry_run:
                        for key, value in org_data.items():
                            setattr(existing, key, value)
                        existing.save()
                        logger.info("Update %s (%s)", org_data["name"], org_data["organization_type"])
                    result.updated += 1
                else:
                    result.unchanged += 1
            else:
                if not dry_run:
                    OrganizationUnit.objects.create(tooi_identifier=tooi, **org_data)
                    logger.info("Create %s (%s)", org_data["name"], org_data["organization_type"])
                result.created += 1

        except Exception as e:
            error_msg = f"Error processing {org_data.get('name', tooi)}: {e}"
            logger.exception(error_msg)
            result.errors.append(error_msg)

    return result
