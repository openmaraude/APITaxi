from flask.ext.restplus import Api as baseApi
from jsonschema import RefResolver
from flask.ext.restplus import Swagger
from werkzeug.utils import cached_property
from . import representations

class Api(baseApi):
    def __init__(self, *args, **kwargs):
        baseApi.__init__(self, *args, **kwargs)
        self.representations = {
            'text/html': representations.output_html,
            'application/json': representations.output_json
        }

    @cached_property
    def resolver(self):
        return RefResolver.from_schema(Swagger(self).as_dict())

    def expect(self, body):
        def wrapper(f):
            def wraps(s, *args, **kwargs):
                s.schema = body.__schema__
                return f(s, *args, **kwargs)
            wraps.__apidoc__ = getattr(f, '__apidoc__', {})
            return super(Api, self).expect(body)(wraps)
        return wrapper
