from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth.models import AnonymousUser, User
from .middleware import ActivityMiddleware
from .models import Activity

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
