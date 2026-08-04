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
    return errors
