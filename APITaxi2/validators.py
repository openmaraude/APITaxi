import dateutil

from flask import jsonify

from marshmallow import fields, Schema, validates, ValidationError


def validate_schema(schema, data):
    try:
        sanitized = schema.load(data)
    except ValidationError as exc:
        # Return None as sanitized data, and the error fields.
        return (None, exc.messages)
    return (sanitized, None)


def make_error_json_response(errors, status_code=400):
    """Parameter errors is a dict as returned by validate_schema().

    Example of the HTTP/400 response return value:

    >>> {
    ...  "errors": {
    ...    "data": {
    ...      "0": {
    ...        "moteur_id": [
    ...          "Not a valid integer."
    ...        ]
    ...      }
    ...    }
    ...  }
    ... }
    """
    return jsonify({'errors': errors}), status_code


def data_schema_wrapper(WrappedSchema):
    """All API endpoints expect input parameters to be under the key "data"
    which is a list of one and only one element: the payload.

    It's probably not the best API design ever (...) but we need to keep this
    behavior for backward-compatibility.
    """

    class DataSchema(Schema):
        data = fields.List(fields.Nested(WrappedSchema))

        @validates('data')
        def validate_length(self, value):
            if len(value) != 1:
                raise ValidationError('Key "data" is expected to be a list of one element.')

    return DataSchema
