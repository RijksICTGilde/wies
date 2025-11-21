import uuid

from wies.core.models import EmailAlias, User
from wies.core.services.errors import EmailNotAvailableError


def get_user_by_email(email):
    """Find user by primary email or alias."""
    user = User.objects.filter(email=email).first()
    if user:
        return user
    alias = EmailAlias.objects.select_related('user').filter(email=email).first()
    return alias.user if alias else None


def create_user(first_name, last_name, email, brand=None, groups=None, email_aliases=None):
    # Validate email availability
    if get_user_by_email(email):
        raise EmailNotAvailableError(email, field='email')
    if email_aliases:
        for alias_email in email_aliases:
            if alias_email == email:
                raise EmailNotAvailableError(alias_email, field='email_aliases')
            if get_user_by_email(alias_email):
                raise EmailNotAvailableError(alias_email, field='email_aliases')

    random_username = uuid.uuid4()
    user = User.objects.create(
        username=random_username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        brand=brand
    )
    if groups:
        user.groups.set(groups)
    if email_aliases:
        for alias_email in email_aliases:
            EmailAlias.objects.create(user=user, email=alias_email)
    return user


def update_user(user, first_name, last_name, email, brand=None, groups=None, email_aliases=None):
    # Validate email availability (exclude current user)
    existing = get_user_by_email(email)
    if existing and existing.pk != user.pk:
        raise EmailNotAvailableError(email, field='email')
    if email_aliases is not None:
        for alias_email in email_aliases:
            if alias_email == email:
                raise EmailNotAvailableError(alias_email, field='email_aliases')
            existing = get_user_by_email(alias_email)
            if existing and existing.pk != user.pk:
                raise EmailNotAvailableError(alias_email, field='email_aliases')

    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.brand = brand
    user.save()
    if groups is not None:
        user.groups.set(groups)
    if email_aliases is not None:
        # Replace all aliases
        user.email_aliases.all().delete()
        for alias_email in email_aliases:
            EmailAlias.objects.create(user=user, email=alias_email)
    return user
