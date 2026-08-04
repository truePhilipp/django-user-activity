from django.apps import AppConfig
from django.core.checks import Error, register


class ActivityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'activity'

    def ready(self):
        register(check_activity_settings)


def check_activity_settings(app_configs, **kwargs):
    from django.conf import settings

    errors = []
    for name in ('ACTIVITY_USER_BLACKLIST', 'ACTIVITY_PATH_PREFIX_BLACKLIST'):
        value = getattr(settings, name, [])
        if not isinstance(value, (list, tuple)):
            errors.append(Error(
                f'{name} must be a list or tuple.',
                obj=f'settings.{name}',
                id='activity.E001',
            ))

    idle_timeout = getattr(settings, 'ACTIVITY_IDLE_TIMEOUT_SECONDS', 30)
    if not isinstance(idle_timeout, (int, float)) or isinstance(idle_timeout, bool) or idle_timeout <= 0:
        errors.append(Error(
            'ACTIVITY_IDLE_TIMEOUT_SECONDS must be a positive number.',
            obj='settings.ACTIVITY_IDLE_TIMEOUT_SECONDS',
            id='activity.E002',
        ))

    engagement_enabled = getattr(settings, 'ACTIVITY_ENGAGEMENT_ENABLED', True)
    if not isinstance(engagement_enabled, bool):
        errors.append(Error(
            'ACTIVITY_ENGAGEMENT_ENABLED must be a bool.',
            obj='settings.ACTIVITY_ENGAGEMENT_ENABLED',
            id='activity.E003',
        ))

    debug_sidebar_enabled = getattr(settings, 'ACTIVITY_DEBUG_SIDEBAR_ENABLED', False)
    if not isinstance(debug_sidebar_enabled, bool):
        errors.append(Error(
            'ACTIVITY_DEBUG_SIDEBAR_ENABLED must be a bool.',
            obj='settings.ACTIVITY_DEBUG_SIDEBAR_ENABLED',
            id='activity.E004',
        ))

    return errors
