import json
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.db.models import F
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import services
from .models import ActivitySettings, ElementInteraction, PageEngagement

VALID_EVENT_TYPES = {ElementInteraction.CLICK, ElementInteraction.INPUT}


def _parse_epoch_ms(value):
    # Client-supplied ms epoch, not server receipt time: a beacon can arrive well after the
    # moment it actually describes (heartbeat delay, retry, etc).
    return datetime.fromtimestamp(float(value) / 1000, tz=dt_timezone.utc)


@csrf_exempt
@require_POST
def record_engagement(request):
    # Sent via navigator.sendBeacon, which cannot set custom headers, so a CSRF
    # token can't be attached. Authentication is still required, and the default
    # SameSite=Lax session cookie keeps cross-site requests from carrying it.
    if not getattr(settings, 'ACTIVITY_ENGAGEMENT_ENABLED', True):
        return HttpResponseNotFound()

    if not request.user.is_authenticated:
        return HttpResponseForbidden('Authentication required')

    try:
        payload = json.loads(request.body)
    except (TypeError, ValueError):
        return HttpResponseBadRequest('Invalid JSON')

    url = payload.get('url')
    if not url or not isinstance(url, str):
        return HttpResponseBadRequest('Missing url')

    visit_id = payload.get('visit_id')
    if not visit_id or not isinstance(visit_id, str):
        return HttpResponseBadRequest('Missing visit_id')

    try:
        visit_started_at = _parse_epoch_ms(payload.get('visit_started_at'))
    except (TypeError, ValueError, OverflowError, OSError):
        return HttpResponseBadRequest('Invalid visit_started_at')

    try:
        active_seconds = float(payload.get('active_seconds', 0))
        idle_seconds = float(payload.get('idle_seconds', 0))
    except (TypeError, ValueError):
        return HttpResponseBadRequest('Invalid metrics')

    interactions = payload.get('interactions', [])
    if not isinstance(interactions, list):
        return HttpResponseBadRequest('Invalid interactions')

    parsed_interactions = []
    for entry in interactions:
        if not isinstance(entry, dict):
            return HttpResponseBadRequest('Invalid interaction entry')
        event_type = entry.get('type')
        xpath = entry.get('xpath')
        if event_type not in VALID_EVENT_TYPES or not xpath or not isinstance(xpath, str):
            return HttpResponseBadRequest('Invalid interaction entry')

        value = entry.get('value')
        if value is not None:
            if not isinstance(value, str):
                return HttpResponseBadRequest('Invalid interaction value')
            value = value[:10000]  # guard against pathological payloads, e.g. a huge paste

        try:
            occurred_at = _parse_epoch_ms(entry.get('at'))
        except (TypeError, ValueError, OverflowError, OSError):
            return HttpResponseBadRequest('Invalid interaction timestamp')

        parsed_interactions.append((event_type, xpath, value, occurred_at))

    if not request.session.session_key:
        request.session.save()

    engagement, created = PageEngagement.objects.get_or_create(
        session_key=request.session.session_key,
        url=url,
        visit_id=visit_id[:64],
        defaults={
            'user': request.user,
            'started_at': visit_started_at,
            'active_seconds': active_seconds,
            'idle_seconds': idle_seconds,
        },
    )
    if not created:
        engagement.active_seconds = F('active_seconds') + active_seconds
        engagement.idle_seconds = F('idle_seconds') + idle_seconds
        engagement.save(update_fields=['active_seconds', 'idle_seconds', 'last_seen_at'])

    ElementInteraction.objects.bulk_create([
        ElementInteraction(engagement=engagement, event_type=event_type, xpath=xpath, value=value, occurred_at=occurred_at)
        for event_type, xpath, value, occurred_at in parsed_interactions
    ])

    return JsonResponse({'status': 'ok'})


def _debug_sidebar_guard(request):
    # The sidebar browses *other users'* full interaction history, including typed field
    # values - the enabled flag alone must never be sufficient to see it.
    if not ActivitySettings.get_solo().debug_sidebar_enabled:
        return HttpResponseNotFound()
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponseForbidden('Staff access required')
    return None


def debug_sessions(request):
    guard = _debug_sidebar_guard(request)
    if guard is not None:
        return guard
    return render(request, 'activity/_debug_sessions.html', {'sessions': services.list_sessions()})


def debug_session_steps(request, session_key):
    guard = _debug_sidebar_guard(request)
    if guard is not None:
        return guard
    return render(
        request,
        'activity/_debug_session_steps.html',
        {'session_key': session_key, 'steps': services.get_session_steps(session_key)},
    )
