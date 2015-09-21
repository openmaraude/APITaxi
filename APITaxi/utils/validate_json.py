#coding: utf-8
from jsonschema import Draft4Validator
from jsonschema.exceptions import ValidationError
from jsonschema import RefResolver
from ..api import api
from flask.ext.restplus import Swagger, abort

def validate(data, model, validator=None):
    resolver = RefResolver.from_schema(Swagger(api).as_dict())
    validator = Draft4Validator(model.__schema__, resolver=resolver)
    try:
        validator.validate(data)
    except ValidationError as e:
        if e.validator == 'maxItems':
            abort(413, message="Maximum size of {} is {}".format(e.relative_path[-1],
                e.validator_value), code=413)
        elif e.validator == 'enum':
            abort(400,
              message='Invalid {}, {}'.format(e.relative_path[-1], e.message))
        abort(400, message=e.message)
