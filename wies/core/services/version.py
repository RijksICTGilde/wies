"""Application version service.

Resolves the running application version from the `APP_VERSION` env var.
- In deployed images, CI bakes the immutable tag in via Dockerfile ARG/ENV.
- In local development, `just up` computes `<branch>-<short-sha>` from git
  and passes it through docker-compose.
"""

import os
from functools import cache
from pathlib import Path

from django.conf import settings

NLDD_VERSION_FILE = Path("wies/core/static/vendor/nldd/VERSION.txt")


@cache
def get_app_version() -> str:
    return os.environ.get("APP_VERSION", "").strip() or "onbekend"


@cache
def get_nldd_version() -> str:
    """The design-system version baked into the vendored bundle.

    Written next to the bundle by scripts/build-nldd.mjs. Used to cache-bust
    the vendor assets in development: runserver serves static straight from
    disk without Cache-Control, so a browser falls back to heuristic caching
    and can keep running a stale ndd.bundle.js after an upgrade — the file name
    itself never changes. Production does not rely on this; WhiteNoise's
    manifest storage content-hashes the names there.

    Empty when the file is missing (a checkout where build-nldd has not run
    yet), in which case the URL is left as-is.
    """
    try:
        first_line = (Path(settings.BASE_DIR) / NLDD_VERSION_FILE).read_text(encoding="utf-8").splitlines()[0]
    except OSError, IndexError:
        return ""
    return first_line.removeprefix("@nldd/design-system").strip()
