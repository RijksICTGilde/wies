import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

from .services.events import create_auth_event

logger = logging.getLogger(__name__)

User = get_user_model()


class AuthBackend(BaseBackend):
    def authenticate(self, request, username=None, email=None, **kwargs):
        if not username:
            msg = "username is required"
            raise ValueError(msg)
        if not email:
            msg = "email is required"
            raise ValueError(msg)

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            logger.info("User not authenticated, user not known.")
            create_auth_event(
                email,
                "Login.fail",
                {
                    "reason": "Unknown user",
                },
            )
            return None

        logger.info("user successfully authenticated")
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
