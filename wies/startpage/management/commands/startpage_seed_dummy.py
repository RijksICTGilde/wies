"""Seed MinIO with a small dummy start page site for local development.

The real publish path (startpage_publish) needs a GitHub release artifact from the
private content repo, which may not exist locally. This dev-only command puts a
browsable placeholder site in the bucket instead, using the *same* storage code
paths as production (ensure_bucket -> upload_site -> set_current_prefix), so
``/odi-startpagina/`` renders end-to-end without the content repo.

Like the real site, the dummy owns its homepage: a root ``index.html`` served at
``/odi-startpagina/`` links to ``/odi-startpagina/kennisbank/``, whose index links
on to ``/odi-startpagina/kennisbank/onboarding/``. There is no separate Django
portal — the mount streams the whole site (homepage included) from MinIO.

Not a TaskCommand: it's run directly (e.g. from ``just setup``), not queued on
the worker.
"""

import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from wies.startpage import storage

_PREFIX = "sites/dummy"

# The real site ships its own homepage at the root (index.html); the mount serves
# it directly (no Django portal). The dummy mirrors that: a root landing page.
_HOME = """<!doctype html>
<html lang="nl"><head><meta charset="utf-8"><title>Start (dummy)</title>
<link rel="stylesheet" href="/odi-startpagina/css/app.css"></head>
<body><h1>Start</h1>
<p>Dit is een lokale dummy-versie van de ODI-startpagina.</p>
<ul><li><a href="/odi-startpagina/kennisbank/">Kennisbank</a></li></ul>
</body></html>
"""

_INDEX = """<!doctype html>
<html lang="nl"><head><meta charset="utf-8"><title>Kennisbank (dummy)</title>
<link rel="stylesheet" href="/odi-startpagina/css/app.css"></head>
<body><h1>Kennisbank</h1>
<p>Dit is een lokale dummy-versie van de kennisbank.</p>
<ul><li><a href="/odi-startpagina/kennisbank/onboarding/">Onboarding</a></li></ul>
<p><a href="/odi-startpagina/">Terug naar start</a></p>
</body></html>
"""

_ONBOARDING = """<!doctype html>
<html lang="nl"><head><meta charset="utf-8"><title>Onboarding (dummy)</title>
<link rel="stylesheet" href="/odi-startpagina/css/app.css"></head>
<body><h1>Onboarding</h1><p>Voorbeeldartikel.</p>
<p><a href="/odi-startpagina/kennisbank/">Terug naar kennisbank</a></p></body></html>
"""

_CSS = "body { font-family: system-ui, sans-serif; max-width: 40rem; margin: 2rem auto; }\n"


class Command(BaseCommand):
    help = "Seed MinIO with a small dummy start page site (local development only)"

    def handle(self, *args, **options):
        # set_current_prefix below repoints the live start page at this placeholder, so
        # refuse to run anywhere DEBUG is off: a stray invocation against a
        # deployed bucket would replace the real site with dummy articles.
        if not settings.DEBUG:
            msg = "startpage_seed_dummy is a development-only command and refuses to run with DEBUG=False"
            raise CommandError(msg)

        client = storage.get_client()
        storage.ensure_bucket(client=client)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # A root homepage (index.html) is served at /odi-startpagina/; the kennisbank's
            # own pages sit under kennisbank/; shared assets (css) stay at the site
            # root so /odi-startpagina/css/app.css resolves for every page.
            (root / "index.html").write_text(_HOME)
            kennisbank = root / "kennisbank"
            kennisbank.mkdir()
            (kennisbank / "index.html").write_text(_INDEX)
            (kennisbank / "onboarding").mkdir()
            (kennisbank / "onboarding" / "index.html").write_text(_ONBOARDING)
            (root / "css").mkdir()
            (root / "css" / "app.css").write_text(_CSS)

            count = storage.upload_site(root, _PREFIX, client=client)

        storage.set_current_prefix(_PREFIX, client=client)
        self.stdout.write(
            self.style.SUCCESS(f"Seeded {count} objects under {_PREFIX!r}; /odi-startpagina/ is now browsable.")
        )
