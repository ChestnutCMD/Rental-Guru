from social_core.exceptions import AuthException


def ensure_email(backend, details, user=None, *args, **kwargs):
    if not user.email:
        raise AuthException(backend, 'Email is required but was not provided by the social provider')
