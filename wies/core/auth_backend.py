from django.contrib.auth.backends import BaseBackend

from .models import Colleague, User
from .services.users import get_user_by_email


class AuthBackend(BaseBackend):

    def authenticate(self, request, username=None, email=None, extra_fields=None):
        if not username:
            raise ValueError('username can\'t be blank!')
        if not email:
            raise ValueError('email cannot be blank!')

        if extra_fields is None:
            extra_fields = {}

        # Try to find user by primary email or alias
        user = get_user_by_email(email)
        if not user:
            return None

        # Link colleague if match on email
        try:
            # this makes sure its matched on ODI email
            matching_colleague = Colleague.objects.get(email=user.email)
            matching_colleague.user = user
            matching_colleague.save()
        except Colleague.DoesNotExist:
            pass

        return user 
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
