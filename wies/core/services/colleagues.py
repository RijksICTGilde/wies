import uuid

from wies.core.models import Colleague

def create_colleague(first_name, last_name, email):
    random_username = uuid.uuid4()
    return Colleague.objects.create(
        username=random_username,
        email=email,
        first_name=first_name,
        last_name=last_name
    )
