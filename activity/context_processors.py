from django.conf import settings
from django.urls import NoReverseMatch, reverse

from .models import ActivitySettings


def engagement(request):
    """Expose the engagement beacon URL (and its config) to every template.

    Lets a consuming project drop in `{% include "activity/engagement_snippet.html" %}`
    instead of hand-wiring the endpoint url and settings into its own base template.
    Returns an empty dict (snippet renders nothing, engagement.js never loads, no beacon is
    ever attempted) if tracking is disabled, the user isn't authenticated, the user is in
    `ACTIVITY_USER_BLACKLIST`, the current page matches `ACTIVITY_PATH_PREFIX_BLACKLIST`, or
    the project never wired `activity.urls` into its URLconf. Same two blacklist settings
    `ActivityMiddleware` already honors for the separate `Activity` request log.
    """
    if not getattr(settings, 'ACTIVITY_ENGAGEMENT_ENABLED', True):
        return {}

    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}

    user_blacklist = getattr(settings, 'ACTIVITY_USER_BLACKLIST', [])
    identifier = getattr(user, user.USERNAME_FIELD, None)
    if identifier in user_blacklist:
        return {}

    path_prefix_blacklist = getattr(settings, 'ACTIVITY_PATH_PREFIX_BLACKLIST', [])
    if any(request.path.startswith(prefix) for prefix in path_prefix_blacklist):
        return {}

    try:
        engagement_url = reverse('activity:record_engagement')
    except NoReverseMatch:
        return {}

    return {
        'ACTIVITY_ENGAGEMENT_URL': engagement_url,
        'ACTIVITY_IDLE_TIMEOUT_SECONDS': getattr(settings, 'ACTIVITY_IDLE_TIMEOUT_SECONDS', 30),
    }


def debug_sidebar(request):
    """Expose whether the developer debug sidebar should render for this request."""
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated or not user.is_staff:
        return {}

    if not ActivitySettings.get_solo().debug_sidebar_enabled:
        return {}

    return {'ACTIVITY_DEBUG_SIDEBAR_ENABLED': True}
