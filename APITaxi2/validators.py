from flask import jsonify

from marshmallow import ValidationError


def validate_schema(schema, data, **kwargs):
    try:
        sanitized = schema.load(data, **kwargs)
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
