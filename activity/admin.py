from django.contrib import admin
from .models import Activity, ElementInteraction, PageEngagement

# Register your models here.
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'url', 'referer', 'method', 'ip', 'user_agent', 'timestamp')
    list_filter = ('method', 'timestamp')
    search_fields = ('user__username', 'url', 'referer', 'method', 'ip')

admin.site.register(Activity, ActivityAdmin)


class ElementInteractionInline(admin.TabularInline):
    model = ElementInteraction
    extra = 0
    fields = ('event_type', 'xpath', 'value', 'occurred_at')
    ordering = ('occurred_at',)


class PageEngagementAdmin(admin.ModelAdmin):
    list_display = ('user', 'url', 'visit_id', 'active_seconds', 'idle_seconds', 'started_at', 'last_seen_at')
    list_filter = ('started_at',)
    search_fields = ('user__username', 'url', 'session_key', 'visit_id')
    inlines = [ElementInteractionInline]

admin.site.register(PageEngagement, PageEngagementAdmin)


class ElementInteractionAdmin(admin.ModelAdmin):
    list_display = ('engagement', 'event_type', 'xpath', 'value', 'occurred_at')
    list_filter = ('event_type', 'occurred_at')
    search_fields = ('xpath', 'value', 'engagement__url', 'engagement__user__username')

admin.site.register(ElementInteraction, ElementInteractionAdmin)
