from django.db import models
from django.contrib.auth.models import User
from solo.models import SingletonModel

# Create your models here.
class Activity(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    url = models.TextField(null=True, blank=True)
    referer = models.TextField(null=True, blank=True)
    method = models.CharField(max_length=10)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'{self.user} visited {self.url} at {self.timestamp}'
    
    class Meta:
        db_table = 'activity'
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'


class PageEngagement(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    url = models.TextField()
    session_key = models.CharField(max_length=40, null=True, blank=True)
    # Generated fresh by engagement.js on every page load (not persisted across reloads), so a
    # visit that ends (navigation, tab close) and a later return to the same url+session become
    # two separate rows instead of accumulating into one forever. Heartbeats sent during the same
    # page load share this id and so still coalesce into a single row.
    visit_id = models.CharField(max_length=64)
    # Client-supplied, like ElementInteraction.occurred_at: the moment the page actually loaded,
    # not when the server happened to receive the first beacon, which can lag by up to
    # HEARTBEAT_MS if the visit ends before its first heartbeat. Set once, at creation, from the
    # payload itself - so it's populated even for a visit that never records any interactions.
    started_at = models.DateTimeField()
    last_seen_at = models.DateTimeField(auto_now=True)
    active_seconds = models.FloatField(default=0)
    idle_seconds = models.FloatField(default=0)

    def __str__(self):
        return f'{self.user} engaged with {self.url} for {self.active_seconds}s'

    class Meta:
        db_table = 'activity_page_engagement'
        verbose_name = 'Page Engagement'
        verbose_name_plural = 'Page Engagements'
        unique_together = ('session_key', 'url', 'visit_id')
        ordering = ['started_at']


class ElementInteraction(models.Model):
    CLICK = 'click'
    INPUT = 'input'
    EVENT_TYPE_CHOICES = [
        (CLICK, 'Click'),
        (INPUT, 'Input'),
    ]

    engagement = models.ForeignKey(PageEngagement, on_delete=models.CASCADE, related_name='interactions')
    event_type = models.CharField(max_length=10, choices=EVENT_TYPE_CHOICES)
    xpath = models.TextField()
    value = models.TextField(null=True, blank=True)
    # Client-supplied, not auto_now_add: several events from one heartbeat/flush arrive in a
    # single request and would otherwise all get the same server-receipt timestamp, destroying
    # the relative order between e.g. two clicks on different elements a few seconds apart.
    occurred_at = models.DateTimeField()

    def __str__(self):
        return f'{self.get_event_type_display()} on {self.xpath} at {self.occurred_at}'

    class Meta:
        db_table = 'activity_element_interaction'
        verbose_name = 'Element Interaction'
        verbose_name_plural = 'Element Interactions'
        ordering = ['occurred_at']


class ActivitySettings(SingletonModel):
    debug_sidebar_enabled = models.BooleanField(
        default=False,
        help_text='Show staff users the debug sidebar, which browses every recorded session including typed field values.',
    )

    def __str__(self):
        return 'Activity Settings'

    class Meta:
        db_table = 'activity_settings'
        verbose_name = 'Activity Settings'
