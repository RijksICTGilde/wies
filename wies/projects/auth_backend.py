from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User


class AuthBackend(BaseBackend):

    def authenticate(self, request, username=None, extra_fields=None):
        if not username:
            raise ValueError('username can\'t be blank!')

        if extra_fields is None:
            extra_fields = {}

        try:
            # TODO: this does not handle if user data is updated after first login
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User(username=username, **extra_fields)
            user.save()

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
