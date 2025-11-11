from django.contrib.auth.backends import BaseBackend

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
            user = Colleague.objects.get(email=email)
        except Colleague.DoesNotExist:
            # do not authenticate if Colleage record does not exist
            return None

        return user 
    
    def get_user(self, user_id):
        try:
            return Colleague.objects.get(pk=user_id)
        except Colleague.DoesNotExist:
            return None
