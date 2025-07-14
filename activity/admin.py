from django.contrib import admin
from .models import Activity

# Register your models here.
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'url', 'referer', 'method', 'ip', 'user_agent', 'timestamp')
    list_filter = ('method', 'timestamp')
    search_fields = ('user__username', 'url', 'referer', 'method', 'ip')

admin.site.register(Activity, ActivityAdmin)
