from flask.ext.restplus import Api as baseApi
from jsonschema import RefResolver
from flask.ext.restplus import Swagger
from werkzeug.utils import cached_property

class Api(baseApi):
    @cached_property
    def resolver(self):
        return RefResolver.from_schema(Swagger(self).as_dict())
