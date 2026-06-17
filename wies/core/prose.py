"""Shared rich-text (prose) editor configuration.

A single extension set is used everywhere a prose editor appears — the
AssignmentCreateForm (``forms.py``) and the inline-edit editables (Service
description, Assignment opdrachtomschrijving) — so the toolbar buttons and the
sanitiser allowlist always match. A button only does something when its
extension is enabled here AND (for sanitised fields) its tags survive nh3, so
heading/blockquote/link must be listed explicitly.
"""

from django_prose_editor.fields import ProseEditorFormField

# Enabled editor features. Keys are django-prose-editor extension names; the
# toolbar is derived from these, so adding/removing a key changes the buttons.
# Used by both the create form and the inline-edit editables via
# ``prose_form_field`` so the toolbar and the nh3 sanitiser allowlist match.
PROSE_EXTENSIONS: dict = {
    "Bold": True,
    "Italic": True,
    "Heading": {"levels": [2, 3]},  # h1 is the page title; offer h2/h3 only
    "BulletList": True,
    "OrderedList": True,
    "ListItem": True,
    "Blockquote": True,
    "Link": True,
}

# Hard upper bound on the stored value. This counts the HTML markup, not just
# the visible text, so it is generous — its purpose is to cap abusive/oversized
# input (storage + render cost), not to constrain normal descriptions. Enforced
# server-side via CharField.max_length (validates the raw POST before nh3) and
# surfaced in the editor as a live character counter (see prose_editor_init.js).
PROSE_MAX_LENGTH = 10_000


def prose_form_field(*, label: str, required: bool = False) -> ProseEditorFormField:
    """ProseEditorFormField with the shared extensions + matching sanitiser."""
    field = ProseEditorFormField(
        label=label,
        required=required,
        max_length=PROSE_MAX_LENGTH,
        extensions=PROSE_EXTENSIONS,
        preset="default",
        sanitize=True,
    )
    # Expose the limit to the rendered <textarea> so the client-side counter
    # (prose_editor_init.js) can read it without hardcoding the number.
    field.widget.attrs["data-prose-maxlength"] = PROSE_MAX_LENGTH
    return field
