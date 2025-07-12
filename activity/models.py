from django.db import models
from django.contrib.auth.models import User

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
        