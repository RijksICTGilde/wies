"""Every <form> carries novalidate, so the server judges the input.

The NLDD fields report their own validity to the form (`required`, and a typed
date or time that is no date or time), and the browser then stops the submit
without a message: a dead save button.
"""

import re
from pathlib import Path

from django.test import TestCase

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "jinja2"

JINJA_COMMENT = re.compile(r"\{#.*?#\}", re.DOTALL)
FORM_TAG = re.compile(r"<form\b[^>]*>", re.IGNORECASE)


class FormsNovalidateTest(TestCase):
    def test_every_form_tag_has_novalidate(self):
        offenders = [
            f"{path.relative_to(TEMPLATE_DIR)}: {' '.join(tag.split())[:80]}"
            for path in sorted(TEMPLATE_DIR.rglob("*.html"))
            for tag in FORM_TAG.findall(JINJA_COMMENT.sub("", path.read_text()))
            if not re.search(r"\snovalidate\b", tag, re.IGNORECASE)
        ]
        assert not offenders, "\n".join(offenders)
