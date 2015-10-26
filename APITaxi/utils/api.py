from flask.ext.restplus import Api, abort
from flask.ext.restplus.model import ApiModel
from jsonschema import RefResolver
from flask.ext.restplus import Swagger
from werkzeug.utils import cached_property
from jsonschema.exceptions import ValidationError
from jsonschema import Draft4Validator

def validate(self, data, resolver=None):
    validator = Draft4Validator(self.__schema__, resolver=resolver)
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

ApiModel.validate = validate

