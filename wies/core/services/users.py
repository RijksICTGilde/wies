import uuid

from wies.core.models import User


def create_user(first_name, last_name, email, brand=None, groups=None):
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
    return user


def update_user(user, first_name, last_name, email, brand=None, groups=None):
    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.brand = brand
    user.save()
    if groups is not None:
        user.groups.set(groups)
    return user
