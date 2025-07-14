from urllib.parse import urlparse
from .models import Activity
import re

class ActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if re.search(r'(log[\-_]?out|sign[\-_]?out)', request.path, re.IGNORECASE):
                self.create_activity(request)
                response = self.get_response(request)
            else:
                response = self.get_response(request)
                self.create_activity(request)
        else:
            response = self.get_response(request)
            
        return response
    
    def create_activity(self, request):
        user = request.user
        path = request.path
        referer = urlparse(request.headers.get('Referer')).path if request.headers.get('Referer') else None
        method = request.method
        ip = request.META.get('HTTP_X_FORWARDED_FOR').split(',')[0] if request.META.get('HTTP_X_FORWARDED_FOR') else request.META.get('REMOTE_ADDR')
        user_agent = request.headers.get('User-Agent')

        Activity.objects.create(
            user=user,
            url=path,
            referer = referer,
            method=method,
            ip=ip,
            user_agent=user_agent
        )
