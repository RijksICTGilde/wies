import json


def user_context(request):
    """Add user context to all templates"""
    user = request.session.get('user')
    if user:
        # If user is a string (JSON), parse it
        if isinstance(user, str):
            try:
                user = json.loads(user)
            except json.JSONDecodeError:
                user = None
    
    return {
        'user': user
    }
