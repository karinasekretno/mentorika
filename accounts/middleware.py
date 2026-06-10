from django.http import HttpResponseForbidden


class BlockChatMediaMiddleware:
    """Chat files are served only through authenticated download views."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path.replace('\\', '/')
        if path.startswith('/media/chat/'):
            return HttpResponseForbidden('Доступ к файлу только через чат.')
        return self.get_response(request)
