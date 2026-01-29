#!/usr/bin/env python3
"""
Analyze organization data from exportOO.xml.

This script parses the large XML file from organisaties.overheid.nl and generates
reports on organization types, top-level organizations, and hierarchy statistics.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from lxml import etree

# Namespace for the XML schema
NS = {"p": "https://organisaties.overheid.nl/static/schema/oo/export/2.6.9"}

# Organization types listed on the organisaties.overheid.nl website
# as top-level categories (from "Direct naar" section)
WEBSITE_TOP_LEVEL_TYPES = [
    "Gemeente",
    "Provincie",
    "Waterschap",
    "Regionaal samenwerkingsorgaan",
    "Gemeenschappelijke regeling",
    "Grensoverschrijdende regionale samenwerkingsorganen",
    "Koepelorganisatie",
    "Grensoverschrijdende gemeenschappelijke regelingen",
    "Caribische openbare lichamen",
    "Aruba, Curaçao en Sint Maarten",
    "Openbare lichamen voor beroep en bedrijf",
    "Kabinet van de Koning",
    "Hoge Colleges van Staat",
    "Ministerie",
    "Agentschap",
    "Interdepartementale commissie",
    "Inspectie",
    "Zelfstandige bestuursorganen",
    "Adviescollege",
    "Politie",
    "Rechtspraak",
    "Overheidsstichtingen of -verenigingen",
    "Externe commissies",
    "Provinciale Rekenkamer",
]


class OrganizationAnalyzer:
    """Analyzer for organization XML data."""

    def __init__(self):
        self.all_types: Counter = Counter()
        self.top_level_types: Counter = Counter()
        self.top_level_examples: dict[str, list[str]] = defaultdict(list)
        self.types_by_level: dict[int, Counter] = defaultdict(Counter)
        self.multi_type_orgs: list[tuple[str, list[str]]] = []
        self.max_depth: int = 0
        self.total_orgs: int = 0
        self.landelijk_dekkende_details: list[dict] = []

    def parse_organization(self, elem: etree.Element, level: int = 0) -> None:
        """
        Recursively parse an organization element and collect statistics.

        Args:
            elem: The organization XML element
            level: Current nesting level (0 = top-level)
        """
        self.total_orgs += 1
        self.max_depth = max(self.max_depth, level)

        # Get organization name
        naam = elem.findtext("p:naam", "", NS)

        # Get all types for this organization
        types = [t.text for t in elem.findall("p:types/p:type", NS) if t.text]

        if not types:
            types = ["<no type>"]

        # Track statistics
        for org_type in types:
            self.all_types[org_type] += 1
            self.types_by_level[level][org_type] += 1

            if level == 0:
                self.top_level_types[org_type] += 1
                # Store examples (limit to 5 per type)
                if len(self.top_level_examples[org_type]) < 5:
                    self.top_level_examples[org_type].append(naam)

        # Track organizations with multiple types
        if len(types) > 1:
            self.multi_type_orgs.append((naam, types))

        # Recursively process nested organizations
        for child_elem in elem.findall("p:organisaties/p:organisatie", NS):
            self.parse_organization(child_elem, level + 1)

    def analyze_file(self, xml_path: Path) -> None:
        """
        Analyze the XML file using iterparse for memory efficiency.

        Args:
            xml_path: Path to the exportOO.xml file
        """
        print(f"Analyzing {xml_path}...")
        print(f"File size: {xml_path.stat().st_size / 1024 / 1024:.1f} MB")
        print()

        # Use iterparse to handle large file efficiently
        context = etree.iterparse(
            str(xml_path),
            events=("end",),
            tag=f"{{{NS['p']}}}organisatie",
        )

        # Track which organizations are top-level
        # (children of the root p:organisaties element)
        for event, elem in context:
            # Check if this is a top-level organization
            # by checking if parent is the root p:organisaties
            parent = elem.getparent()
            if parent is not None and parent.tag == f"{{{NS['p']}}}organisaties":
                grandparent = parent.getparent()
                # Top-level if grandparent is overheidsorganisaties
                if grandparent is not None and grandparent.tag == f"{{{NS['p']}}}overheidsorganisaties":
                    # IMPORTANT: Parse the organization and its children BEFORE clearing
                    self.parse_organization(elem, level=0)

                    # Now safe to clear - parsing is complete
                    elem.clear()

            # Clean up previous siblings to free memory
            while elem.getprevious() is not None:
                del elem.getparent()[0]

        del context

        # Second pass specifically for Landelijk dekkende samenwerkingen analysis
        # This needs full element access before clearing
        self._analyze_landelijk_dekkende_organizations(xml_path)

    def _analyze_landelijk_dekkende_organizations(self, xml_path: Path) -> None:
        """
        Second pass to analyze 'Landelijk dekkende samenwerkingen' in detail.
        This requires full element access.

        Args:
            xml_path: Path to the XML file
        """
        tree = etree.parse(str(xml_path))
        root = tree.getroot()

        # Find all top-level Landelijk dekkende samenwerkingen organizations
        for org in root.findall("p:organisaties/p:organisatie", NS):
            types = [t.text for t in org.findall("p:types/p:type", NS) if t.text]

            if "Landelijk dekkende samenwerkingen" in types:
                naam = org.findtext("p:naam", "", NS)

                # Count children
                children = org.findall("p:organisaties/p:organisatie", NS)
                child_count = len(children)

                # Get child names
                child_names = []
                if children:
                    for child in children[:10]:  # Limit to first 10
                        child_naam = child.findtext("p:naam", "", NS)
                        if child_naam:
                            child_names.append(child_naam)

                # Get description
                beschrijving = org.findtext("p:beschrijving", "", NS)

                self.landelijk_dekkende_details.append(
                    {
                        "naam": naam,
                        "child_count": child_count,
                        "child_names": child_names,
                        "beschrijving": beschrijving,
                    }
                )

    def print_report(self) -> None:
        """Print the analysis report to stdout."""
        self._print_header("ORGANIZATION ANALYSIS REPORT")

        print(f"Total organizations analyzed: {self.total_orgs:,}")
        print(f"Maximum hierarchy depth: {self.max_depth}")
        print()

        self._print_all_types()
        self._print_top_level_types()
        self._print_website_comparison()
        self._print_landelijk_dekkende_analysis()
        self._print_hierarchy_distribution()
        self._print_multi_type_organizations()

    def _print_header(self, title: str) -> None:
        """Print a formatted section header."""
        print("=" * 80)
        print(title.center(80))
        print("=" * 80)
        print()

    def _print_all_types(self) -> None:
        """Print all organization types found."""
        print("-" * 80)
        print("ALL ORGANIZATION TYPES FOUND")
        print("-" * 80)
        print()
        print(f"Total unique types: {len(self.all_types)}")
        print()

        # Sort by count (descending)
        for org_type, count in self.all_types.most_common():
            percentage = (count / self.total_orgs) * 100
            print(f"  {org_type:<50} {count:>6,} ({percentage:>5.1f}%)")
        print()

    def _print_top_level_types(self) -> None:
        """Print organization types found at top level."""
        print("-" * 80)
        print("TOP-LEVEL ORGANIZATIONS (No Parents)")
        print("-" * 80)
        print()
        print(f"Total top-level organizations: {sum(self.top_level_types.values()):,}")
        print()

        # Sort by count (descending)
        for org_type, count in self.top_level_types.most_common():
            print(f"\n{org_type}: {count}")
            print("  Examples:")
            for example in self.top_level_examples[org_type]:
                print(f"    - {example}")
        print()

    def _print_website_comparison(self) -> None:
        """Compare XML top-level types with website categories."""
        print("-" * 80)
        print("COMPARISON WITH WEBSITE CATEGORIES")
        print("-" * 80)
        print()

        # Normalize types for comparison (lowercase, strip plurals, etc.)
        def normalize(type_name: str) -> str:
            """Normalize type name for comparison."""
            normalized = type_name.lower().strip()
            # Handle plural forms
            if normalized.endswith("en"):
                normalized = normalized[:-2]  # Remove "en" plural
            if normalized.endswith("s"):
                normalized = normalized[:-1]  # Remove "s" plural
            return normalized

        # Build sets of normalized types
        website_normalized = {normalize(t): t for t in WEBSITE_TOP_LEVEL_TYPES}
        xml_normalized = {normalize(t): t for t in self.top_level_types.keys()}

        # Find matches and differences
        matched = set(website_normalized.keys()) & set(xml_normalized.keys())
        only_website = set(website_normalized.keys()) - set(xml_normalized.keys())
        only_xml = set(xml_normalized.keys()) - set(website_normalized.keys())

        print(f"Website categories: {len(WEBSITE_TOP_LEVEL_TYPES)}")
        print(f"XML top-level types: {len(self.top_level_types)}")
        print(f"Matched (normalized): {len(matched)}")
        print()

        if only_website:
            print("Categories on WEBSITE but NOT in XML top-level:")
            for norm_type in sorted(only_website):
                orig_type = website_normalized[norm_type]
                print(f"  - {orig_type}")
            print()

        if only_xml:
            # Define singular forms that have plural matches on website (expected differences)
            expected_singular_forms = {
                "Caribisch openbaar lichaam",  # Website: "Caribische openbare lichamen"
                "Grensoverschrijdend regionaal samenwerkingsorgaan",  # Website: plural form
                "Hoog College van Staat",  # Website: "Hoge Colleges van Staat"
                "Openbaar lichaam voor beroep en bedrijf",  # Website: "Openbare lichamen..."
                "Overheidsstichting of -vereniging",  # Website: "Overheidsstichtingen..."
                "Zelfstandig bestuursorgaan",  # Website: "Zelfstandige bestuursorganen"
                "Organisatieonderdeel",  # Expected nested type
            }

            filtered_only_xml = []
            for norm_type in only_xml:
                orig_type = xml_normalized[norm_type]
                if orig_type not in expected_singular_forms:
                    filtered_only_xml.append((norm_type, orig_type))

            if filtered_only_xml:
                print("Types in XML top-level but NOT on WEBSITE:")
                print("(excluding singular forms with plural website matches and expected types)")
                for norm_type, orig_type in sorted(filtered_only_xml, key=lambda x: x[1]):
                    count = self.top_level_types[orig_type]
                    print(f"  - {orig_type} ({count} organizations)")
                print()
            else:
                print("No unexpected types in XML top-level (all differences are expected)")
                print()

        if matched:
            print(f"Matched categories ({len(matched)}):")
            for norm_type in sorted(matched):
                website_type = website_normalized[norm_type]
                xml_type = xml_normalized[norm_type]
                count = self.top_level_types[xml_type]
                if website_type != xml_type:
                    print(f"  - Website: '{website_type}' → XML: '{xml_type}' ({count})")
                else:
                    print(f"  - {xml_type} ({count})")
            print()

    def _print_landelijk_dekkende_analysis(self) -> None:
        """Analyze 'Landelijk dekkende samenwerkingen' organizations in detail."""
        print("-" * 80)
        print("LANDELIJK DEKKENDE SAMENWERKINGEN ANALYSIS")
        print("-" * 80)
        print()

        if not self.landelijk_dekkende_details:
            print("No 'Landelijk dekkende samenwerkingen' organizations found.")
            print()
            return

        print(f"Total: {len(self.landelijk_dekkende_details)} organizations")
        print()

        has_children_count = sum(1 for org in self.landelijk_dekkende_details if org["child_count"] > 0)
        no_children_count = len(self.landelijk_dekkende_details) - has_children_count

        print(f"Organizations WITH children: {has_children_count}")
        print(f"Organizations WITHOUT children (meta-categories): {no_children_count}")
        print()

        print("Detailed breakdown:")
        print()

        for org in sorted(self.landelijk_dekkende_details, key=lambda x: x["naam"]):
            print(f"  {org['naam']}")
            print(f"    Children: {org['child_count']}")

            if org["child_count"] > 0:
                print("    Child organizations:")
                for child_naam in org["child_names"]:
                    print(f"      - {child_naam}")
                if org["child_count"] > len(org["child_names"]):
                    remaining = org["child_count"] - len(org["child_names"])
                    print(f"      ... and {remaining} more")
            else:
                print("    → META-CATEGORY (no actual child hierarchy)")

            if org["beschrijving"]:
                # Truncate long descriptions
                desc = org["beschrijving"][:200]
                if len(org["beschrijving"]) > 200:
                    desc += "..."
                print(f"    Description: {desc}")

            print()

    def _print_hierarchy_distribution(self) -> None:
        """Print distribution of types across hierarchy levels."""
        print("-" * 80)
        print("HIERARCHY DISTRIBUTION")
        print("-" * 80)
        print()

        for level in sorted(self.types_by_level.keys()):
            total_at_level = sum(self.types_by_level[level].values())
            print(f"Level {level} ({total_at_level:,} organizations):")

            # Show top 5 types at this level
            for org_type, count in self.types_by_level[level].most_common(5):
                percentage = (count / total_at_level) * 100
                print(f"  {org_type:<45} {count:>6,} ({percentage:>5.1f}%)")

            # Show "..." if there are more types
            if len(self.types_by_level[level]) > 5:
                remaining = len(self.types_by_level[level]) - 5
                print(f"  ... and {remaining} more type(s)")

            print()

    def _print_multi_type_organizations(self) -> None:
        """Print organizations that have multiple types."""
        print("-" * 80)
        print("ORGANIZATIONS WITH MULTIPLE TYPES")
        print("-" * 80)
        print()

        if not self.multi_type_orgs:
            print("No organizations with multiple types found.")
            print()
            return

        print(f"Total: {len(self.multi_type_orgs)}")
        print()

        # Show up to 20 examples
        for naam, types in self.multi_type_orgs[:20]:
            print(f"  {naam}")
            print(f"    Types: {', '.join(types)}")
            print()

        if len(self.multi_type_orgs) > 20:
            print(f"  ... and {len(self.multi_type_orgs) - 20} more")
            print()

    def export_json(self, output_path: Path) -> None:
        """
        Export analysis results as JSON for further processing.

        Args:
            output_path: Path to write JSON file
        """
        data = {
            "summary": {
                "total_organizations": self.total_orgs,
                "max_depth": self.max_depth,
                "unique_types": len(self.all_types),
            },
            "all_types": dict(self.all_types),
            "top_level_types": dict(self.top_level_types),
            "top_level_examples": dict(self.top_level_examples),
            "types_by_level": {str(level): dict(counter) for level, counter in self.types_by_level.items()},
            "multi_type_orgs": self.multi_type_orgs,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"JSON report exported to: {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analyze organization data from exportOO.xml")
    parser.add_argument(
        "xml_file",
        nargs="?",
        default="exportOO.xml",
        help="Path to the exportOO.xml file (default: exportOO.xml)",
    )
    parser.add_argument(
        "--json",
        "-j",
        metavar="FILE",
        help="Export results as JSON to the specified file",
    )

    args = parser.parse_args()

    xml_path = Path(args.xml_file)

    if not xml_path.exists():
        print(f"Error: File not found: {xml_path}")
        return 1

    analyzer = OrganizationAnalyzer()
    analyzer.analyze_file(xml_path)
    analyzer.print_report()

    if args.json:
        analyzer.export_json(Path(args.json))

    return 0


if __name__ == "__main__":
    exit(main())
