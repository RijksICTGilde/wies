#!/usr/bin/env python3
"""
Script to convert Django templates to Jinja2 templates.
"""
import re
from pathlib import Path


def convert_django_to_jinja2(content):
    """Convert Django template syntax to Jinja2 syntax."""

    # Remove {% load static %} and {% load ... %}
    content = re.sub(r'{%\s*load\s+\w+\s*%}\n?', '', content)

    # Convert {% static 'path' %} to {{ static('path') }}
    content = re.sub(r"{%\s*static\s+'([^']+)'\s*%}", r"{{ static('\1') }}", content)
    content = re.sub(r'{%\s*static\s+"([^"]+)"\s*%}', r'{{ static("\1") }}', content)

    # Convert {% comment %}...{% endcomment %} to {# ... #}
    content = re.sub(r'{%\s*comment\s*%}(.*?){%\s*endcomment\s*%}', r'{# \1 #}', content, flags=re.DOTALL)

    # Convert {% csrf_token %} to CSRF token helper function
    content = re.sub(
        r'{%\s*csrf_token\s*%}',
        r'{{ get_csrf_hidden_input(request) }}',
        content
    )

    # Convert {% empty %} to {% else %} in for loops
    content = re.sub(r'{%\s*empty\s*%}', r'{% else %}', content)

    # Convert {{ var|default:"text" }} to {{ var|default("text") }}
    content = re.sub(r'\|default:"([^"]*)"', r'|default("\1")', content)
    content = re.sub(r"\|default:'([^']*)'", r"|default('\1')", content)

    # Convert {{ var|add:"-5" }} to {{ var - 5 }}
    content = re.sub(r'\{\{\s*(\w+(?:\.\w+)*)\|add:"(-?\d+)"\s*\}\}', r'{{ \1 + \2 }}', content)

    # Convert forloop.last to loop.last
    content = re.sub(r'forloop\.last', 'loop.last', content)
    content = re.sub(r'forloop\.first', 'loop.first', content)
    content = re.sub(r'forloop\.counter', 'loop.index', content)
    content = re.sub(r'forloop\.counter0', 'loop.index0', content)
    # Note: forloop.parentloop requires manual fix with {% set outer_loop = loop %}

    # Convert .exists to .exists()
    content = re.sub(r'(\w+(?:\.\w+)*)\.exists\b(?!\()', r'\1.exists()', content)

    # Convert .count to .count()
    content = re.sub(r'(\w+(?:\.\w+)*)\.count\b(?!\()', r'\1.count()', content)

    # Convert .all to .all()
    content = re.sub(r'(\w+(?:\.\w+)*)\.all\b(?!\()', r'\1.all()', content)

    # Convert Django's get_*_display methods to get_*_display()
    content = re.sub(r'\.get_(\w+)_display\b(?!\()', r'.get_\1_display()', content)

    # Convert |slice:":3" to [:3]
    content = re.sub(r'\|slice:"(\d*):(\d*)"', lambda m: f"[{m.group(1) or ''}:{m.group(2) or ''}]", content)

    # Convert user.get_full_name to user.get_full_name()
    content = re.sub(r'user\.get_full_name\b(?!\()', r'user.get_full_name()', content)

    # Convert {% url 'name' arg %} to {{ url('name', args=[arg]) }}
    # Simple case: {% url 'name' %}
    content = re.sub(r"{%\s*url\s+'([^']+)'\s*%}", r"{{ url('\1') }}", content)
    # Variable URL name: {% url url_name %}
    content = re.sub(r"{%\s*url\s+(\w+)\s*%}", r"{{ url(\1) }}", content)
    # With one positional argument: {% url 'name' var %}
    content = re.sub(r"{%\s*url\s+'([^']+)'\s+(\w+(?:\.\w+)*)\s*%}", r"{{ url('\1', args=[\2]) }}", content)
    # With keyword arguments: {% url 'name' pk=var %}
    content = re.sub(r"{%\s*url\s+'([^']+)'\s+(\w+)=(\w+(?:\.\w+)*)\s*%}", r"{{ url('\1', \2=\3) }}", content)

    # Convert {% include 'template.html' with var=value %} to {% with var=value %}{% include 'template.html' %}{% endwith %}
    def include_with_handler(match):
        template = match.group(1)
        params = match.group(2)
        # Replace spaces with commas for Jinja2 syntax
        # Handle quoted values with spaces: key="value with spaces" key2="value2"
        params_fixed = re.sub(r'("[^"]*")\s+(\w+=)', r'\1, \2', params)
        params_fixed = re.sub(r"('[^']*')\s+(\w+=)", r'\1, \2', params_fixed)
        # Handle unquoted values: key=value key2=value2
        while re.search(r'(\w+=[^\s,]+)\s+(\w+=)', params_fixed):
            params_fixed = re.sub(r'(\w+=[^\s,]+)\s+(\w+=)', r'\1, \2', params_fixed)
        return f'{{% with {params_fixed} %}}{{% include "{template}" %}}{{% endwith %}}'

    content = re.sub(r'{%\s*include\s+"([^"]+)"\s+with\s+(.+?)\s*%}', include_with_handler, content)
    content = re.sub(r"{%\s*include\s+'([^']+)'\s+with\s+(.+?)\s*%}", include_with_handler, content)

    # Fix {% with %} statements to use comma-separated arguments
    # This handles standalone {% with %} blocks
    def fix_with_statement(match):
        params = match.group(1)
        # Replace spaces between var=value pairs with commas
        params_fixed = re.sub(r"(\w+=['\"][^'\"]*['\"])\s+(\w+=['\"])", r'\1, \2', params)
        params_fixed = re.sub(r"(\w+=[^\s'\"]+)\s+(\w+=)", r'\1, \2', params_fixed)
        # Handle multiple params (repeat until no more matches)
        while re.search(r"(\w+=[^\s,]+)\s+(\w+=)", params_fixed):
            params_fixed = re.sub(r"(\w+=[^\s,]+)\s+(\w+=)", r'\1, \2', params_fixed)
        return f"{{% with {params_fixed} %}}"

    content = re.sub(r"{%\s*with\s+([^%]+)\s*%}", fix_with_statement, content)

    # Convert string concatenation with |add filter to ~ operator
    # '-'|add:field -> '-' ~ field
    content = re.sub(r"'([^']*)'\|add:(\w+(?:\.\w+)*)", r"'\1' ~ \2", content)
    content = re.sub(r'"([^"]*)"\|add:(\w+(?:\.\w+)*)', r'"\1" ~ \2', content)

    # Convert {{ block.super }} to {{ super() }}
    content = re.sub(r'\{\{\s*block\.super\s*\}\}', r'{{ super() }}', content)

    # Convert {% widthratio a b c %} to {{ (a / b * c)|int }}
    content = re.sub(
        r'{%\s*widthratio\s+(\w+(?:\.\w+)*)\s+(\w+(?:\.\w+)*)\s+(\d+)\s*%}',
        r'{{ ((\1 / \2 * \3) | int) if \2 else 0 }}',
        content
    )

    # Convert custom template tags
    # {% placements_url_with_filters 'name' %}
    content = re.sub(
        r"{%\s*placements_url_with_filters\s+'([^']+)'\s*%}",
        r"{{ placements_url_with_filters(request, '\1') }}",
        content
    )

    # {% assignments_url_with_tab tab_key %}
    content = re.sub(
        r"{%\s*assignments_url_with_tab\s+(\w+)\s*%}",
        r"{{ assignments_url_with_tab(request, \1) }}",
        content
    )

    # Convert Django filter syntax to Jinja2 native syntax
    # |yesno:'true,false' -> ternary operator
    content = re.sub(r"\|yesno\('true,false'\)", r" if True else 'false'", content)
    content = re.sub(r'\|yesno\("true,false"\)', r' if True else "false"', content)

    # Convert Django date filter to strftime
    # |date("M Y") -> .strftime("%b %Y")
    date_format_map = {
        'M Y': '%b %Y',
        'F Y': '%B %Y',
        'd-m-Y': '%d-%m-%Y',
        'j M Y': '%-d %b %Y',
        'd-m-Y H:i': '%d-%m-%Y %H:%M',
        'M y': '%b %y',
        'd M Y': '%d %b %Y',
    }
    for django_fmt, strftime_fmt in date_format_map.items():
        content = re.sub(rf'\|date\("{django_fmt}"\)', rf'.strftime("{strftime_fmt}")', content)
        content = re.sub(rf"\|date\('{django_fmt}'\)", rf".strftime('{strftime_fmt}')", content)

    # Convert pluralize to ternary operator
    # Note: This only handles the simple case of pluralize("en")
    # For other patterns, manual conversion may be needed
    content = re.sub(r'\|pluralize\("([^"]*)"\)', r' if != 1 else ""', content)
    content = re.sub(r"\|pluralize\('([^']*)'\)", r" if != 1 else ''", content)

    # Convert truncatechars to slicing with ellipsis
    # |truncatechars(20) -> ([:17] ~ '...') if |length > 20 else
    # Note: This is complex and may need manual adjustment

    # |stringformat:"s" -> |string
    content = re.sub(r'\|stringformat:"s"', r'|string', content)
    content = re.sub(r"\|stringformat:'s'", r'|string', content)

    # Convert .items, .keys, .values to method calls
    content = re.sub(r'\.items\s*%}', r'.items() %}', content)
    content = re.sub(r'\.keys\s*%}', r'.keys() %}', content)
    content = re.sub(r'\.values\s*%}', r'.values() %}', content)

    # Convert None to none (Jinja2 uses lowercase)
    content = re.sub(r'\bis None\b', r'is none', content)
    content = re.sub(r'\bis not None\b', r'is not none', content)

    return content


def convert_file(source_path, dest_path):
    """Convert a single template file."""
    print(f"Converting {source_path} -> {dest_path}")

    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()

    converted_content = convert_django_to_jinja2(content)

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write(converted_content)


def main():
    base_dir = Path(__file__).parent
    projects_templates = base_dir / "wies" / "projects" / "templates"
    projects_jinja2 = base_dir / "wies" / "projects" / "jinja2"

    exact_templates = base_dir / "wies" / "exact" / "templates" / "exact"
    exact_jinja2 = base_dir / "wies" / "exact" / "jinja2" / "exact"

    # Convert projects templates
    for template_file in projects_templates.rglob("*.html"):
        relative_path = template_file.relative_to(projects_templates)
        dest_file = projects_jinja2 / relative_path
        convert_file(template_file, dest_file)

    # Convert exact templates
    for template_file in exact_templates.rglob("*.html"):
        relative_path = template_file.relative_to(exact_templates)
        dest_file = exact_jinja2 / relative_path
        convert_file(template_file, dest_file)

    print("\nConversion complete!")
    print("\nPost-conversion steps needed:")
    print("1. Run: find wies/projects/jinja2 -name '*.html' -type f -exec sed -i '' 's/|date:\"\\([^\"]*\\)\"/|date(\"\\1\")/g' {} \\;")
    print("2. Run: find wies/exact/jinja2 -name '*.html' -type f -exec sed -i '' 's/|date:\"\\([^\"]*\\)\"/|date(\"\\1\")/g' {} \\;")
    print("3. Run: find wies/projects/jinja2 -name '*.html' -type f -exec sed -i '' 's/\\.get_absolute_url }/\\.get_absolute_url() }/g' {} \\;")
    print("\nManual review needed for:")
    print("- Complex {% url %} tags with multiple arguments")
    print("- Date filters - verify Django format conversion to strftime")
    print("- Form rendering - ensure field.errors, field.id_for_label still work")
    print("- CSRF tokens in JavaScript - verify get_csrf_token(request) works in AJAX")
    print("- Any custom template tags not covered")


if __name__ == "__main__":
    main()
