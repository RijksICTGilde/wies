from django.contrib.auth.backends import BaseBackend

from .models import Colleague, User


class AuthBackend(BaseBackend):

    def authenticate(self, request, username=None, email=None, extra_fields=None):
        if not username:
            raise ValueError('username can\'t be blank!')
        if not email:
            raise ValueError('email cannot be blank!')

        if extra_fields is None:
            extra_fields = {}

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # do not authenticate if Colleage record does not exist
            return None

        # Link colleague if match on email
        try:
            matching_colleague = Colleague.objects.get(email=email)
            matching_colleague.user = user
            matching_colleague.save()
        except Colleague.DoesNotExist:
            pass

        return user 
    
    # TODO: update tests on this, now returning colleage instead of user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
