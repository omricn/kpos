class ForceHttpsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.META['wsgi.url_scheme'] = 'https'
        return self.get_response(request)
