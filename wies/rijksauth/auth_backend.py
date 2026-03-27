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

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
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
