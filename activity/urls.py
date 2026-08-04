from django.urls import path
from . import views

app_name = 'activity'

urlpatterns = [
    path('engagement/', views.record_engagement, name='record_engagement'),
    path('debug/sessions/', views.debug_sessions, name='debug_sessions'),
    path('debug/sessions/<str:session_key>/', views.debug_session_steps, name='debug_session_steps'),
]
