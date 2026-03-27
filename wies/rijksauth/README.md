# django-rijksauth

Reusable Django app for OIDC authentication in Dutch government projects. Works with any OIDC-compliant provider (Keycloak, Azure AD, etc.) via authlib's generic OIDC client.

> **Note:** This app currently lives inside the Wies project at `wies/rijksauth/`. Import paths below use `wies.rijksauth.*`. When extracted as a standalone package, these will become `rijksauth.*`.

## What's included

- **`User` model** — email-based authentication (no username), extends `AbstractUser`
- **`AuthEvent` model** — audit log for login events (`Login.success`, `Login.fail`) with timestamp, email, and JSON context
- **`AuthBackend`** — authenticates users by email lookup
- **Auth views** — `login` (redirect to OIDC provider), `auth` (OIDC callback), `logout`
- **`AutoLoginMiddleware`** — auto-login for local dev when OIDC provider is unreachable
- **`ensure_initial_user`** — management command to bootstrap a first admin user from environment variables (idempotent)
- **`user_logged_in` signal** — Django's built-in signal, fired on successful login. Use this to hook in post-login logic (e.g. linking domain objects to the user)

## Installation

```python
INSTALLED_APPS = [
    # ...
    "wies.rijksauth",  # or "rijksauth" when installed as standalone package
    # ...
]

AUTH_USER_MODEL = "rijksauth.User"

AUTHENTICATION_BACKENDS = [
    "wies.rijksauth.auth_backend.AuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]
```

## Required settings

| Setting              | Description                                          |
| -------------------- | ---------------------------------------------------- |
| `OIDC_CLIENT_ID`     | OIDC client ID from your OIDC provider               |
| `OIDC_CLIENT_SECRET` | OIDC client secret from your OIDC provider           |
| `OIDC_DISCOVERY_URL` | OIDC discovery endpoint URL                          |
| `AUTH_NO_ACCESS_URL` | Redirect URL when login fails (user not in database) |

## Optional settings

| Setting                  | Default | Description                                                                 |
| ------------------------ | ------- | --------------------------------------------------------------------------- |
| `SKIP_OIDC`              | `false` | Enable auto-login middleware for dev                                        |
| `INITIAL_USER_EMAIL`     |         | Email for an initial user (`ensure_initial_user`), added to all user groups |
| `INITIAL_USER_FIRSTNAME` |         | First name for the initial user (optional)                                  |
| `INITIAL_USER_LASTNAME`  |         | Last name for the initial user (optional)                                   |

## URL configuration

Wire up the auth views in your `urls.py`:

```python
from wies.rijksauth.views import auth, login, logout

urlpatterns = [
    path("inloggen/", login, name="login"),
    path("auth/", auth, name="auth"),
    path("uitloggen/", logout, name="logout"),
]
```

## Extending with a user profile

The `rijksauth.User` model is intentionally minimal: just email-based authentication. Your project will likely need additional user metadata (roles, labels, department, phone number, etc.). The recommended pattern is a **separate profile model** in your own app with a `OneToOneField` to `User`:

```python
# yourapp/models.py
from django.conf import settings
from django.db import models

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    department = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    # ... any fields specific to your project
```

### Service layer for user management

Wrap user + profile creation in a service function so the two are always created together:

```python
# yourapp/services/users.py
from django.contrib.auth import get_user_model

from yourapp.models import UserProfile

User = get_user_model()

def create_user(email, first_name, last_name, department="", ...):
    user = User.objects.create_user(
        email=email, first_name=first_name, last_name=last_name,
    )
    UserProfile.objects.create(user=user, department=department, ...)
    return user

def update_user(user, first_name, last_name, department="", ...):
    user.first_name = first_name
    user.last_name = last_name
    user.save(update_fields=["first_name", "last_name"])

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.department = department
    profile.save(update_fields=["department"])
    return user
```

### Linking profiles on first login

Use the `user_logged_in` signal to ensure a profile exists after OIDC login (the user may have been created by `ensure_initial_user` or an admin, without a profile):

```python
# yourapp/signals.py
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from yourapp.models import UserProfile

@receiver(user_logged_in)
def ensure_profile_on_login(sender, request, user, **kwargs):
    UserProfile.objects.get_or_create(user=user)
```

Register the signal in your app's `ready()` method:

```python
# yourapp/apps.py
class YourAppConfig(AppConfig):
    def ready(self):
        import yourapp.signals  # noqa: F401, PLC0415
```

This way your app owns the full user lifecycle.

## Enforcing email domains

`rijksauth` authenticates any user that exists in the database — it does not restrict which email domains are allowed. Domain enforcement is project-specific and belongs in your app, for instance in the `create_user` service function:

```python
def create_user(email, ...):
    validate_email_domain(email)
    # ... create user and profile
```

## No-access page

When a user logs in via OIDC but doesn't exist in the database, rijksauth redirects to `AUTH_NO_ACCESS_URL`. Point this to your own view that explains which domains are allowed and how to request access. The failed email is available in `request.session["failed_login_email"]` so you can show a tailored message.
