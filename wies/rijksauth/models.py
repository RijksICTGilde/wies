from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            msg = "Email is required"
            raise ValueError(msg)
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractUser):
    username = None
    email = models.EmailField()

    # Set once the user has seen (completed or skipped) the first-login
    # onboarding wizard. While None, the wizard is shown on every page.
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "auth_user"
        constraints = [
            models.UniqueConstraint(Lower("email"), name="unique_user_email_ci"),
        ]


class AuthEvent(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user_email = models.EmailField(max_length=255, blank=True, db_index=True)
    name = models.CharField(max_length=32, db_index=True)
    context = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.name} ({self.user_email})"
