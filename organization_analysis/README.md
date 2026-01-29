# Organization Analysis

Folder to investigate what an effective org chart would look like. It contains:

- `exportOO.xml` - Source data from organisaties.overheid.nl
- `oo-export-2.6.11.xsd` - XML schema
- `analyze_organizations.py` script to get organization types, hierarchy distribution, and statistics
- `generate_hierarchy.py` script to generate hierarchical JSON structure for visualization, using custom rules to make it more usable.
- `hierarchy.json` - Generated hierarchy
- `visualize.html` - Interactive hierarchy viewer
- `organogrammen/` - Ministry organizational charts

## Scripts

### analyze_organizations.py

Analyzes organization types, hierarchy distribution, and statistics.

```bash
# Basic usage
uv run python analyze_organizations.py exportOO.xml

# Export JSON summary
uv run python analyze_organizations.py exportOO.xml --json results.json
```

### generate_hierarchy.py

Generates hierarchical JSON structure for visualization.

```bash
# Generate hierarchy
uv run python generate_hierarchy.py exportOO.xml -o hierarchy.json

# View in browser
open visualize.html
```
