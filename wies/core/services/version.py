"""Application version service.

Resolves the running application version from the `APP_VERSION` env var.
- In deployed images, CI bakes the immutable tag in via Dockerfile ARG/ENV.
- In local development, `just up` computes `<branch>-<short-sha>` from git
  and passes it through docker-compose.
"""

import os
from functools import cache


@cache
def get_app_version() -> str:
    return os.environ.get("APP_VERSION", "").strip() or "onbekend"
