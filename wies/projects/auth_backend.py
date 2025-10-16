from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
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
            colleague = Colleague.objects.get(email=email)
        except Colleague.DoesNotExist:
            # do not authenticate if Colleague record does not exist
            return None

        try:
            # TODO: this does not handle if user data is updated after first login
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User(username=username, email=email, **extra_fields)
            user.save()
        
        # if not yet linked, link
        if not colleague.user:
            colleague.user = user
            colleague.save()

        return user 
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
