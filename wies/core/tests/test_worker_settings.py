import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

REPO_ROOT = Path(__file__).resolve().parents[3]

# Env the subprocess starts from. We deliberately provide only DJANGO_SECRET_KEY
# (which every settings module requires) and omit all OIDC_* variables. If the
# worker settings ever start pulling in production.py's OIDC credential lookups
# again, django.setup() will raise KeyError and this test fails.
MINIMAL_ENV = {
    "PATH": "/usr/bin:/bin",
    "DJANGO_SETTINGS_MODULE": "config.settings.worker",
    "DJANGO_SECRET_KEY": "smoke-test-secret-key",
}


class WorkerSettingsSmokeTest(SimpleTestCase):
    """The db_worker never performs OIDC login, so config.settings.worker must
    boot without any OIDC_* env vars. Run django.setup() in a clean subprocess
    to lock that promise in — an in-process check can't, because the OIDC vars
    are already loaded into os.environ by the test runner."""

    def test_django_setup_without_oidc_env(self):
        result = subprocess.run(
            [sys.executable, "-c", "import django; django.setup()"],
            cwd=REPO_ROOT,
            env=MINIMAL_ENV,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert result.returncode == 0, (
            f"django.setup() failed under config.settings.worker without OIDC env.\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
