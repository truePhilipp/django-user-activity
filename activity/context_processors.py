from django.conf import settings
from django.urls import NoReverseMatch, reverse


def engagement(request):
    """Expose the engagement beacon URL (and its config) to every template.

    Lets a consuming project drop in `{% include "activity/engagement_snippet.html" %}`
    instead of hand-wiring the endpoint url and settings into its own base template.
    Returns an empty dict (snippet renders nothing) if tracking is disabled, the user
    isn't authenticated, or the project never wired `activity.urls` into its URLconf.
    """
    if not getattr(settings, 'ACTIVITY_ENGAGEMENT_ENABLED', True):
        return {}

    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}

    try:
        engagement_url = reverse('activity:record_engagement')
    except NoReverseMatch:
        return {}

    return {
        'ACTIVITY_ENGAGEMENT_URL': engagement_url,
        'ACTIVITY_IDLE_TIMEOUT_SECONDS': getattr(settings, 'ACTIVITY_IDLE_TIMEOUT_SECONDS', 30),
    }
