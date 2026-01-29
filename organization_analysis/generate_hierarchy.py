#!/usr/bin/env python3
"""
Generate hierarchical JSON from exportOO.xml government organization data.

This script creates a practical hierarchy by:
1. Grouping ministry-affiliated organizations under their ministries
2. Grouping independent bodies by type
3. Preserving nested organizational units
4. Filtering out meta-categories with no actual hierarchy
"""

import argparse
import json
from pathlib import Path

from lxml import etree

# Namespace for the XML schema
NS = {"p": "https://organisaties.overheid.nl/static/schema/oo/export/2.6.9"}


# Types that should be grouped independently (no ministry affiliation expected)
INDEPENDENT_TYPES = {
    "Hoog College van Staat",  # Singular form
    "Hoge Colleges van Staat",  # Plural form
    "Kabinet van de Koning",
    "Rechtspraak",
    "Caribisch openbaar lichaam",
    "Aruba, Curaçao en Sint Maarten",
}

# Local/regional government types
LOCAL_GOVERNMENT_TYPES = {
    "Gemeente",
    "Provincie",
    "Waterschap",
    "Regionaal samenwerkingsorgaan",
    "Gemeenschappelijke regeling",
    "Grensoverschrijdend regionaal samenwerkingsorgaan",
    "Grensoverschrijdende gemeenschappelijke regeling",
}


class HierarchyNode:
    """Represents a node in the organization hierarchy."""

    def __init__(self, label: str):
        self.label = label
        self.children: list[HierarchyNode] = []
        self.system_id: str | None = None
        self.org_type: str | None = None

    def add_child(self, child: "HierarchyNode") -> None:
        """Add a child node."""
        self.children.append(child)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {"label": self.label}
        if self.children:
            result["children"] = [child.to_dict() for child in self.children]
        return result

    def sort_children(self) -> None:
        """Recursively sort all children alphabetically."""
        self.children.sort(key=lambda x: x.label)
        for child in self.children:
            child.sort_children()


class HierarchyGenerator:
    """Generates hierarchy from organization XML data."""

    def __init__(self):
        self.ministries: dict[str, HierarchyNode] = {}
        self.type_groups: dict[str, HierarchyNode] = {}
        self.root = HierarchyNode("(container) Nederlandse Overheid")
        self.processed_ids: set[str] = set()

    def parse_organization(
        self,
        elem: etree.Element,
        parent_ministry: str | None = None,
    ) -> HierarchyNode | None:
        """
        Parse an organization element and create a hierarchy node.

        Args:
            elem: The organization XML element
            parent_ministry: Ministry name from parent context

        Returns:
            HierarchyNode or None if organization should be skipped
        """
        # Get basic info
        naam = elem.findtext("p:naam", "", NS).strip()
        if not naam:
            return None

        system_id = elem.get(f"{{{NS['p']}}}systeemId")

        # Skip duplicates
        if system_id and system_id in self.processed_ids:
            return None
        if system_id:
            self.processed_ids.add(system_id)

        # Get types
        types = [t.text.strip() for t in elem.findall("p:types/p:type", NS) if t.text]
        if not types:
            types = ["Overheidsorganisatie"]  # Default type

        primary_type = types[0]

        # Check for ministry affiliation
        ministry_elem = elem.find("p:relatieMetMinisterie", NS)
        ministry_name = None
        if ministry_elem is not None and ministry_elem.text:
            ministry_name = ministry_elem.text.strip()
        elif parent_ministry:
            ministry_name = parent_ministry

        # Create node
        node = HierarchyNode(naam)
        node.system_id = system_id
        node.org_type = primary_type

        # Check if this is a meta-category (Landelijk dekkende samenwerkingen with no children)
        if "Landelijk dekkende samenwerkingen" in types:
            child_orgs = elem.findall("p:organisaties/p:organisatie", NS)
            if not child_orgs:
                # Meta-category with no actual hierarchy - skip
                return None

        # Recursively process children
        for child_elem in elem.findall("p:organisaties/p:organisatie", NS):
            child_node = self.parse_organization(child_elem, ministry_name)
            if child_node:
                node.add_child(child_node)

        return node

    def should_group_under_ministry(self, org_type: str) -> bool:
        """
        Determine if an organization type should be grouped under its ministry.

        Args:
            org_type: The primary organization type

        Returns:
            True if should be grouped under ministry
        """
        # Don't group if it's an independent type
        if org_type in INDEPENDENT_TYPES:
            return False

        # Don't group local/regional government
        if org_type in LOCAL_GOVERNMENT_TYPES:
            return False

        # Don't group if it IS a ministry
        if org_type == "Ministerie":
            return False

        # Don't group "Organisatie met overheidsbemoeienis" under ministry
        if org_type == "Organisatie met overheidsbemoeienis":
            return False

        # Don't group "Overheidsstichting of -vereniging" under ministry
        if org_type == "Overheidsstichting of -vereniging":
            return False

        # Group everything else under ministry if affiliated
        return True

    def organize_into_hierarchy(self, organizations: list[HierarchyNode]) -> None:
        """
        Organize flat list of organizations into hierarchical structure.

        Args:
            organizations: List of parsed organization nodes
        """
        # Create category containers
        ministries_container = HierarchyNode("Ministeries")
        local_gov_container = HierarchyNode("Decentrale Overheden")

        for org in organizations:
            org_type = org.org_type or "Overheidsorganisatie"

            # Handle Ministries
            if org_type == "Ministerie":
                ministries_container.add_child(org)
                # Store reference for grouping affiliated organizations
                self.ministries[org.label] = org
                continue

            # Handle Local/Regional Government
            if org_type in LOCAL_GOVERNMENT_TYPES:
                # Create type group if needed
                if org_type not in self.type_groups:
                    self.type_groups[org_type] = HierarchyNode(org_type)
                    local_gov_container.add_child(self.type_groups[org_type])

                self.type_groups[org_type].add_child(org)
                continue

            # Handle Independent Bodies
            if org_type in INDEPENDENT_TYPES:
                # Create type group if needed
                if org_type not in self.type_groups:
                    self.type_groups[org_type] = HierarchyNode(org_type)
                    self.root.add_child(self.type_groups[org_type])

                self.type_groups[org_type].add_child(org)
                continue

            # Everything else: try to group under ministry or by type
            # This needs a second pass after ministries are registered

        # Second pass: attach ministry-affiliated organizations
        ministry_affiliated: dict[str, list[HierarchyNode]] = {}

        for org in organizations:
            if org.org_type == "Ministerie":
                continue
            if org.org_type in LOCAL_GOVERNMENT_TYPES:
                continue
            if org.org_type in INDEPENDENT_TYPES:
                continue

            # Check if this should be grouped under a ministry
            # We need to find which ministry this belongs to
            # This is tricky because we parsed recursively
            # Let's use a different approach...

        # Add top-level containers to root
        if ministries_container.children:
            ministries_container.sort_children()
            self.root.add_child(ministries_container)

        if local_gov_container.children:
            local_gov_container.sort_children()
            self.root.add_child(local_gov_container)

    def build_hierarchy_direct(self, xml_path: Path) -> HierarchyNode:
        """
        Build hierarchy directly from XML using a different strategy.

        Parse top-level organizations and decide placement based on:
        1. Is it a Ministry? -> Goes under Ministeries
        2. Has ministry affiliation and should be grouped? -> Under that Ministry
        3. Is local/regional government? -> Group by type under Decentrale Overheden
        4. Is independent body? -> Group by type at root level
        5. Other types with ministry -> Create "Overige Rijksorganisaties" under ministry

        Args:
            xml_path: Path to the XML file

        Returns:
            Root hierarchy node
        """
        print(f"Parsing {xml_path}...")

        tree = etree.parse(str(xml_path))
        root_elem = tree.getroot()

        # Create category containers
        ministries_container = HierarchyNode("(type) Ministerie")
        local_gov_container = HierarchyNode("(container) Decentrale Overheden")
        other_container = HierarchyNode("(container) Overige Organisaties")

        # First pass: collect all ministries
        for org_elem in root_elem.findall("p:organisaties/p:organisatie", NS):
            types = [t.text.strip() for t in org_elem.findall("p:types/p:type", NS) if t.text]
            if types and types[0] == "Ministerie":
                ministry_node = self.parse_organization(org_elem)
                if ministry_node:
                    ministries_container.add_child(ministry_node)
                    self.ministries[ministry_node.label] = ministry_node

        # Second pass: collect affiliated organizations
        for org_elem in root_elem.findall("p:organisaties/p:organisatie", NS):
            system_id = org_elem.get(f"{{{NS['p']}}}systeemId")
            if system_id in self.processed_ids:
                continue

            types = [t.text.strip() for t in org_elem.findall("p:types/p:type", NS) if t.text]
            if not types:
                continue

            primary_type = types[0]

            # Skip ministries (already processed)
            if primary_type == "Ministerie":
                continue

            # Parse the organization
            org_node = self.parse_organization(org_elem)
            if not org_node:
                continue

            # Check for ministry affiliation
            ministry_elem = org_elem.find("p:relatieMetMinisterie", NS)
            ministry_name = ministry_elem.text.strip() if ministry_elem is not None and ministry_elem.text else None

            # Categorize
            if primary_type in LOCAL_GOVERNMENT_TYPES:
                # Local/regional government
                if primary_type not in self.type_groups:
                    type_label = f"(type) {primary_type}"
                    self.type_groups[primary_type] = HierarchyNode(type_label)
                    local_gov_container.add_child(self.type_groups[primary_type])
                self.type_groups[primary_type].add_child(org_node)

            elif primary_type in INDEPENDENT_TYPES:
                # Independent bodies
                if primary_type not in self.type_groups:
                    type_label = f"(type) {primary_type}"
                    self.type_groups[primary_type] = HierarchyNode(type_label)
                    self.root.add_child(self.type_groups[primary_type])
                self.type_groups[primary_type].add_child(org_node)

            elif ministry_name and self.should_group_under_ministry(primary_type):
                # Try to find the ministry
                ministry_node = None
                for min_name, min_node in self.ministries.items():
                    # Match ministry name (handle variations)
                    if ministry_name.lower() in min_name.lower() or min_name.lower() in ministry_name.lower():
                        ministry_node = min_node
                        break

                if ministry_node:
                    # Only create type subgroups for well-known types
                    # Organizational units go directly under ministry
                    if primary_type in {
                        "Agentschap",
                        "Inspectie",
                        "Adviescollege",
                        "Zelfstandig bestuursorgaan",
                        "Interdepartementale commissie",
                        "Politie",
                    }:
                        # Create type subgroup under ministry
                        type_group = None
                        type_group_label = f"(type) {primary_type}"
                        for child in ministry_node.children:
                            if child.label == type_group_label:
                                type_group = child
                                break

                        if not type_group:
                            type_group = HierarchyNode(type_group_label)
                            ministry_node.add_child(type_group)

                        type_group.add_child(org_node)
                    else:
                        # Other types (like Organisatieonderdeel) go directly under ministry
                        ministry_node.add_child(org_node)
                else:
                    # Couldn't find ministry, put in other
                    other_container.add_child(org_node)

            else:
                # Other organizations
                if primary_type not in self.type_groups:
                    type_label = f"(type) {primary_type}"
                    self.type_groups[primary_type] = HierarchyNode(type_label)
                    other_container.add_child(self.type_groups[primary_type])
                self.type_groups[primary_type].add_child(org_node)

        # Sort and add containers to root
        if ministries_container.children:
            ministries_container.sort_children()
            self.root.add_child(ministries_container)

        if local_gov_container.children:
            local_gov_container.sort_children()
            self.root.add_child(local_gov_container)

        if other_container.children:
            other_container.sort_children()
            self.root.add_child(other_container)

        # Sort independent type groups
        for type_name in sorted(self.type_groups.keys()):
            if type_name in INDEPENDENT_TYPES:
                self.type_groups[type_name].sort_children()

        return self.root

    def generate_json(self, output_path: Path, indent: int = 2) -> None:
        """
        Generate JSON output file.

        Args:
            output_path: Path to write JSON file
            indent: JSON indentation level (None for compact)
        """
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                self.root.to_dict(),
                f,
                indent=indent,
                ensure_ascii=False,
            )

        print(f"Hierarchy JSON written to: {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate hierarchical JSON from exportOO.xml")
    parser.add_argument(
        "xml_file",
        nargs="?",
        default="exportOO.xml",
        help="Path to the exportOO.xml file (default: exportOO.xml)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="hierarchy.json",
        help="Output JSON file path (default: hierarchy.json)",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Generate compact JSON (no indentation)",
    )

    args = parser.parse_args()

    xml_path = Path(args.xml_file)
    if not xml_path.exists():
        print(f"Error: File not found: {xml_path}")
        return 1

    generator = HierarchyGenerator()
    generator.build_hierarchy_direct(xml_path)

    indent = None if args.compact else 2
    generator.generate_json(Path(args.output), indent=indent)

    # Print some stats
    total_orgs = len(generator.processed_ids)
    print("\nStatistics:")
    print(f"  Total organizations processed: {total_orgs}")
    print(f"  Ministries: {len(generator.ministries)}")
    print(f"  Type groups: {len(generator.type_groups)}")

    return 0


if __name__ == "__main__":
    exit(main())
