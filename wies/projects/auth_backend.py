from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from .models import Colleague


class AuthBackend(BaseBackend):

    def authenticate(self, request, username=None, email=None, extra_fields=None):
        if not username:
            raise ValueError('username can\'t be blank!')
        if not email:
            raise ValueError('email cannot be blank!')

        if extra_fields is None:
            extra_fields = {}

        try:
            # TODO: this does not handle if user data is updated after first login
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User(username=username, email=email, **extra_fields)
            user.save()

        # Link or create Colleague profile
        name = f"{user.first_name} {user.last_name}".strip()
        colleague, _ = Colleague.objects.get_or_create(
            email=email,
            defaults={'name': name}
        )
        
        # if not yet linked, link
        if not colleague.user:
            colleague.user = user
            colleague.save()

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
