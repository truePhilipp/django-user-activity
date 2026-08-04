import json
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase, override_settings
from django.urls import NoReverseMatch

from .context_processors import engagement
from .middleware import ActivityMiddleware
from .models import Activity, ElementInteraction, PageEngagement
from .views import record_engagement

# Create your tests here.
class ActivityMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.middleware = ActivityMiddleware(lambda request: request)

    def test_activity_created_for_authenticated_user(self):
        request = self.factory.get('/dashboard/')
        request.user = self.user
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.headers = {
            'Referer': 'http://testserver.com/home/',
            'User-Agent': 'TestAgent/1.0'
        }

        self.middleware(request)

        activity = Activity.objects.last()
        self.assertIsNotNone(activity)
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.url, '/dashboard/')
        self.assertEqual(activity.referer, '/home/')
        self.assertEqual(activity.method, 'GET')
        self.assertEqual(activity.ip, '127.0.0.1')
        self.assertEqual(activity.user_agent, 'TestAgent/1.0')

    def test_activity_created_for_logout_path(self):
        request = self.factory.get('/logout/')
        request.user = self.user
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.headers = {}

        self.middleware(request)

        self.assertEqual(Activity.objects.count(), 1)
        self.assertEqual(Activity.objects.first().url, '/logout/')

    def test_no_activity_for_unauthenticated_user(self):
        request = self.factory.get('/dashboard/')
        request.user = AnonymousUser()
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.headers = {}

        self.middleware(request)

        self.assertEqual(Activity.objects.count(), 0)

    def test_ip_from_x_forwarded_for(self):
        request = self.factory.get('/page/')
        request.user = self.user
        request.META['HTTP_X_FORWARDED_FOR'] = '192.168.1.100, 10.0.0.1'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.headers = {}

        self.middleware(request)

        activity = Activity.objects.last()
        self.assertEqual(activity.ip, '192.168.1.100')

    @override_settings(ACTIVITY_USER_BLACKLIST=['testuser'])
    def test_no_activity_for_blacklisted_user(self):
        request = self.factory.get('/dashboard/')
        request.user = self.user
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.headers = {}

        self.middleware(request)

        self.assertEqual(Activity.objects.count(), 0)

    @override_settings(ACTIVITY_PATH_PREFIX_BLACKLIST=['/admin/'])
    def test_no_activity_for_blacklisted_path_prefix(self):
        request = self.factory.get('/admin/settings/')
        request.user = self.user
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.headers = {}

        self.middleware(request)

        self.assertEqual(Activity.objects.count(), 0)

    def test_logout_path_regex_variants(self):
        logout_paths = ['/logout/', '/sign-out/', '/LogOut', '/SIGN_OUT']
        for path in logout_paths:
            Activity.objects.all().delete()

            request = self.factory.get(path)
            request.user = self.user
            request.META['REMOTE_ADDR'] = '127.0.0.1'
            request.headers = {}

            self.middleware(request)

            self.assertEqual(Activity.objects.count(), 1)
            self.assertEqual(Activity.objects.first().url, path)


class _StubSession:
    def __init__(self, session_key=None):
        self.session_key = session_key

    def save(self):
        if not self.session_key:
            self.session_key = 'stub-session-key'


class RecordEngagementViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='password')

    def _make_request(self, user, payload, session_key='stub-session-key'):
        if isinstance(payload, dict):
            payload = {'visit_id': 'stub-visit-id', 'visit_started_at': 1000, **payload}
        body = payload if isinstance(payload, str) else json.dumps(payload)
        request = self.factory.post('/activity/engagement/', data=body, content_type='application/json')
        request.session = _StubSession(session_key)
        request.user = user
        return request

    def test_creates_engagement_for_authenticated_user(self):
        request = self._make_request(self.user, {
            'url': '/dashboard/',
            'active_seconds': 12.5,
            'idle_seconds': 3,
            'visit_started_at': 500,
            'interactions': [
                {'type': 'click', 'xpath': '//*[@id="submit"]', 'at': 1000},
                {'type': 'input', 'xpath': '/html/body/form[1]/input[1]', 'value': 'hello', 'at': 2000},
            ],
        })

        response = record_engagement(request)

        self.assertEqual(response.status_code, 200)
        engagement = PageEngagement.objects.last()
        self.assertIsNotNone(engagement)
        self.assertEqual(engagement.user, self.user)
        self.assertEqual(engagement.url, '/dashboard/')
        self.assertEqual(engagement.active_seconds, 12.5)
        self.assertEqual(engagement.idle_seconds, 3)
        self.assertEqual(engagement.started_at.timestamp(), 0.5)

        click = ElementInteraction.objects.get(engagement=engagement, event_type='click')
        self.assertEqual(click.xpath, '//*[@id="submit"]')
        self.assertIsNone(click.value)

        input_interaction = ElementInteraction.objects.get(engagement=engagement, event_type='input')
        self.assertEqual(input_interaction.xpath, '/html/body/form[1]/input[1]')
        self.assertEqual(input_interaction.value, 'hello')
        self.assertLess(click.occurred_at, input_interaction.occurred_at)

    def test_engagement_gets_started_at_even_without_interactions(self):
        request = self._make_request(self.user, {'url': '/dashboard/', 'visit_started_at': 1500})

        record_engagement(request)

        engagement = PageEngagement.objects.get(session_key='stub-session-key', url='/dashboard/')
        self.assertEqual(engagement.started_at.timestamp(), 1.5)

    def test_started_at_is_not_overwritten_by_later_beacons(self):
        record_engagement(self._make_request(self.user, {'url': '/dashboard/', 'visit_started_at': 1000}))
        record_engagement(self._make_request(self.user, {'url': '/dashboard/', 'visit_started_at': 9999}))

        engagement = PageEngagement.objects.get(session_key='stub-session-key', url='/dashboard/')
        self.assertEqual(engagement.started_at.timestamp(), 1)

    def test_rejects_missing_visit_started_at(self):
        request = self._make_request(self.user, {'url': '/dashboard/', 'visit_started_at': None})

        response = record_engagement(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PageEngagement.objects.count(), 0)

    def test_orders_engagements_by_started_at_not_creation_order(self):
        record_engagement(self._make_request(self.user, {'url': '/b/', 'visit_id': 'visit-b', 'visit_started_at': 5000}))
        record_engagement(self._make_request(self.user, {'url': '/a/', 'visit_id': 'visit-a', 'visit_started_at': 1000}))

        urls = list(PageEngagement.objects.filter(session_key='stub-session-key').values_list('url', flat=True))
        self.assertEqual(urls, ['/a/', '/b/'])

    def test_each_interaction_is_logged_as_its_own_row_in_order(self):
        request = self._make_request(self.user, {
            'url': '/dashboard/',
            'interactions': [
                {'type': 'click', 'xpath': '//*[@id="a"]', 'at': 1000},
                {'type': 'click', 'xpath': '//*[@id="b"]', 'at': 2000},
                {'type': 'click', 'xpath': '//*[@id="a"]', 'at': 3000},
            ],
        })

        record_engagement(request)

        engagement = PageEngagement.objects.get(session_key='stub-session-key', url='/dashboard/')
        interactions = list(ElementInteraction.objects.filter(engagement=engagement).order_by('occurred_at'))
        self.assertEqual([i.xpath for i in interactions], ['//*[@id="a"]', '//*[@id="b"]', '//*[@id="a"]'])

    def test_repeated_input_beacons_each_create_a_new_row(self):
        record_engagement(self._make_request(self.user, {
            'url': '/dashboard/',
            'interactions': [{'type': 'input', 'xpath': '//*[@id="name"]', 'value': 'hel', 'at': 1000}],
        }))
        record_engagement(self._make_request(self.user, {
            'url': '/dashboard/',
            'interactions': [{'type': 'input', 'xpath': '//*[@id="name"]', 'value': 'hello', 'at': 2000}],
        }))

        engagement = PageEngagement.objects.get(session_key='stub-session-key', url='/dashboard/')
        values = list(
            ElementInteraction.objects.filter(engagement=engagement, event_type='input')
            .order_by('occurred_at')
            .values_list('value', flat=True)
        )
        self.assertEqual(values, ['hel', 'hello'])

    def test_rejects_missing_interaction_timestamp(self):
        request = self._make_request(self.user, {
            'url': '/dashboard/',
            'interactions': [{'type': 'click', 'xpath': '//*[@id="submit"]'}],
        })

        response = record_engagement(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PageEngagement.objects.count(), 0)

    def test_rejects_non_string_interaction_value(self):
        request = self._make_request(self.user, {
            'url': '/dashboard/',
            'interactions': [{'type': 'input', 'xpath': '//*[@id="name"]', 'value': 123}],
        })

        response = record_engagement(request)

        self.assertEqual(response.status_code, 400)

    def test_accumulates_on_repeated_beacons(self):
        record_engagement(self._make_request(self.user, {'url': '/dashboard/', 'active_seconds': 10}))
        record_engagement(self._make_request(self.user, {'url': '/dashboard/', 'active_seconds': 5}))

        engagement = PageEngagement.objects.get(session_key='stub-session-key', url='/dashboard/')
        self.assertEqual(engagement.active_seconds, 15)

    def test_repeated_clicks_on_same_element_each_create_a_row(self):
        payload = {'url': '/dashboard/', 'interactions': [{'type': 'click', 'xpath': '//*[@id="submit"]', 'at': 1000}]}
        record_engagement(self._make_request(self.user, payload))
        record_engagement(self._make_request(self.user, payload))

        engagement = PageEngagement.objects.get(session_key='stub-session-key', url='/dashboard/')
        self.assertEqual(ElementInteraction.objects.filter(engagement=engagement, event_type='click').count(), 2)

    def test_rejects_invalid_interaction_entry(self):
        request = self._make_request(self.user, {
            'url': '/dashboard/',
            'interactions': [{'type': 'hover', 'xpath': '//*[@id="submit"]'}],
        })

        response = record_engagement(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PageEngagement.objects.count(), 0)

    def test_rejects_missing_visit_id(self):
        request = self._make_request(self.user, {'url': '/dashboard/', 'visit_id': None})

        response = record_engagement(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PageEngagement.objects.count(), 0)

    def test_different_visit_ids_create_separate_engagement_rows(self):
        record_engagement(self._make_request(self.user, {'url': '/dashboard/', 'active_seconds': 10, 'visit_id': 'visit-a'}))
        record_engagement(self._make_request(self.user, {'url': '/dashboard/', 'active_seconds': 5, 'visit_id': 'visit-b'}))

        self.assertEqual(PageEngagement.objects.filter(session_key='stub-session-key', url='/dashboard/').count(), 2)
        visit_a = PageEngagement.objects.get(session_key='stub-session-key', url='/dashboard/', visit_id='visit-a')
        visit_b = PageEngagement.objects.get(session_key='stub-session-key', url='/dashboard/', visit_id='visit-b')
        self.assertEqual(visit_a.active_seconds, 10)
        self.assertEqual(visit_b.active_seconds, 5)

    def test_same_visit_id_accumulates_across_beacons(self):
        record_engagement(self._make_request(self.user, {'url': '/dashboard/', 'active_seconds': 10, 'visit_id': 'visit-a'}))
        record_engagement(self._make_request(self.user, {'url': '/dashboard/', 'active_seconds': 5, 'visit_id': 'visit-a'}))

        self.assertEqual(PageEngagement.objects.filter(session_key='stub-session-key', url='/dashboard/').count(), 1)
        engagement = PageEngagement.objects.get(session_key='stub-session-key', url='/dashboard/', visit_id='visit-a')
        self.assertEqual(engagement.active_seconds, 15)

    def test_rejects_unauthenticated_user(self):
        request = self._make_request(AnonymousUser(), {'url': '/dashboard/', 'active_seconds': 1})

        response = record_engagement(request)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(PageEngagement.objects.count(), 0)

    def test_rejects_malformed_json(self):
        request = self._make_request(self.user, 'not-json')

        response = record_engagement(request)

        self.assertEqual(response.status_code, 400)

    def test_rejects_missing_url(self):
        request = self._make_request(self.user, {'active_seconds': 1})

        response = record_engagement(request)

        self.assertEqual(response.status_code, 400)

    @override_settings(ACTIVITY_ENGAGEMENT_ENABLED=False)
    def test_disabled_returns_not_found(self):
        request = self._make_request(self.user, {'url': '/dashboard/', 'active_seconds': 1})

        response = record_engagement(request)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(PageEngagement.objects.count(), 0)


class EngagementContextProcessorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='password')

    def test_exposes_url_and_idle_timeout_for_authenticated_user(self):
        request = self.factory.get('/dashboard/')
        request.user = self.user

        context = engagement(request)

        self.assertIn('ACTIVITY_ENGAGEMENT_URL', context)
        self.assertTrue(context['ACTIVITY_ENGAGEMENT_URL'].endswith('/engagement/'))
        self.assertEqual(context['ACTIVITY_IDLE_TIMEOUT_SECONDS'], 30)

    @override_settings(ACTIVITY_IDLE_TIMEOUT_SECONDS=45)
    def test_reflects_custom_idle_timeout_setting(self):
        request = self.factory.get('/dashboard/')
        request.user = self.user

        context = engagement(request)

        self.assertEqual(context['ACTIVITY_IDLE_TIMEOUT_SECONDS'], 45)

    def test_empty_for_unauthenticated_user(self):
        request = self.factory.get('/dashboard/')
        request.user = AnonymousUser()

        self.assertEqual(engagement(request), {})

    @override_settings(ACTIVITY_ENGAGEMENT_ENABLED=False)
    def test_empty_when_disabled(self):
        request = self.factory.get('/dashboard/')
        request.user = self.user

        self.assertEqual(engagement(request), {})

    def test_empty_when_urls_not_wired(self):
        request = self.factory.get('/dashboard/')
        request.user = self.user

        with patch('activity.context_processors.reverse', side_effect=NoReverseMatch):
            self.assertEqual(engagement(request), {})
