import uuid

from wies.core.models import User


def create_user(first_name, last_name, email, brand=None):
    random_username = uuid.uuid4()
    return User.objects.create(
        username=random_username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        brand=brand
    )
