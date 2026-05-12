import logging

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from wies.core.models import Colleague

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def link_colleague_on_login(sender, request, user, **kwargs):
    """Link or create a Colleague for the User on login.

    Only looks at source="wies" colleagues. OTYS-imported colleagues are matched
    separately during sync — TODO: handle OTYS-imported users here when that's implemented.
    """
    colleague = Colleague.objects.filter(email__iexact=user.email, source="wies").first()
    if colleague is not None:
        if colleague.user_id != user.id:
            colleague.user = user
            colleague.save(update_fields=["user"])
    else:
        Colleague.objects.create(
            user=user,
            name=f"{user.first_name} {user.last_name}".strip() or user.email,
            email=user.email,
            source="wies",
        )
