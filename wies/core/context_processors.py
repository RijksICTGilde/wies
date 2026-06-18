from wies.core.services.rijksprofielservice import get_cached_profile


def rijksprofielservice(request):
    if not request.user.is_authenticated:
        return {}
    return {"rijksprofielservice_profile": get_cached_profile(request)}
