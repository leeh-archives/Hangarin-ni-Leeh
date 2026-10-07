from django.conf import settings


def social_login(request):
    """Lets the login and sign-up pages know which provider buttons to show."""
    return {
        "google_enabled": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
        "github_enabled": bool(settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET),
    }
