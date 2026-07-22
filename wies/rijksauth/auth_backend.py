import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .services.events import create_auth_event

logger = logging.getLogger(__name__)

User = get_user_model()


class AuthBackend(ModelBackend):
    def authenticate(self, request, username=None, email=None, *, email_verified=False, **kwargs):
        # `username` carries the OIDC `sub` claim (see rijksauth.views.auth).
        if not username:
            msg = "username is required"
            raise ValueError(msg)
        if not email:
            msg = "email is required"
            raise ValueError(msg)

        # A token whose email is not verified upstream is never trusted, on any path.
        if not email_verified:
            logger.info("User not authenticated, email not verified.")
            create_auth_event(email, "Login.fail", {"reason": "Email not verified"}, request=request)
            return None

        oidc_sub = username

        # Stable path: the one account bound to this subject.
        # protects against the email adress being changed by attacker
        try:
            user = User.objects.get(oidc_sub=oidc_sub)
        except User.DoesNotExist:
            user = None
        if user is not None:
            logger.info("user successfully authenticated")
            return user

        # First login for this subject: claim a pre-provisioned account by email,
        # but ONLY while it is still unbound.
        claimed = User.objects.filter(email__iexact=email, oidc_sub__isnull=True).update(oidc_sub=oidc_sub)
        if claimed:
            logger.info("user successfully authenticated, bound OIDC subject on first login")
            return User.objects.get(oidc_sub=oidc_sub)

        # No unbound account with this email: either the user is unknown, or the
        # email is already bound to a different subject. Deny either way.
        logger.info("User not authenticated, no unbound account for subject/email.")
        create_auth_event(
            email,
            "Login.fail",
            {
                "reason": "Unknown user or email already bound to another account",
            },
            request=request,
        )
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
