from django.urls import path
from . import views

app_name = 'activity'

urlpatterns = [
    path('engagement/', views.record_engagement, name='record_engagement'),
]
