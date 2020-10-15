class ForceJSONContentTypeMiddleware:
    """This API only accepts JSON for POST, PUT and PATCH requests. The
    previous API version didn't require clients to provide a Content-Type at
    all.

    This middleware forces Content-Type to be application/json for edition
    requests in case it is not provided.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        if environ['REQUEST_METHOD'] in ('POST', 'PUT', 'PATCH') and not environ.get('CONTENT_TYPE'):
            environ['CONTENT_TYPE'] = 'application/json'
        return self.wsgi_app(environ, start_response)
