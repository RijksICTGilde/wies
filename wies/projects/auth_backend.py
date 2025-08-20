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
        full_name = f"{user.first_name} {user.last_name}".strip()
        display_name = full_name if full_name else username
        self._ensure_colleague_profile(user, email, display_name)

        return user
    
    def _ensure_colleague_profile(self, user, email, name):
        """Ensure user has a linked colleague profile"""
        # Check if user already has a colleague linked
        if hasattr(user, 'colleague') and user.colleague:
            return
        
        # Get or create colleague by email, then link to user
        colleague, created = Colleague.objects.get_or_create(
            email=email,
            defaults={'name': name, 'user': user}
        )
        
        # If colleague existed but wasn't linked, link it now
        if not created and not colleague.user:
            colleague.user = user
            colleague.save()

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
