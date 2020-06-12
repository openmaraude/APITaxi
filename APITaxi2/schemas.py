from marshmallow import (
    decorators,
    EXCLUDE,
    fields,
    Schema,
    validate,
    validates,
    validates_schema,
    ValidationError,
)

from APITaxi_models2.vehicle import UPDATABLE_VEHICLE_STATUS

from . import redis_backend


class DepartementSchema(Schema):
    nom = fields.String()
    numero = fields.String()

    @validates_schema
    def check_required(self, data, **kwargs):
        if 'nom' not in data and 'numero' not in data:
            raise ValidationError(
                'You need to specify at least "nom" or "numero"', 'nom'
            )


class DriverSchema(Schema):
    first_name = fields.String(required=True)
    last_name = fields.String(required=True)
    birth_date = fields.Date(allow_none=True)
    professional_licence = fields.String(required=True, allow_none=False)
    departement = fields.Nested(DepartementSchema, required=True)


class RefADSSchema(Schema):
    numero = fields.String(required=True, allow_none=False)
    insee = fields.String(required=True, allow_none=False)


class ADSSchema(RefADSSchema):
    category = fields.String(required=True)
    vehicle_id = fields.Int(allow_none=True)
    owner_name = fields.String(required=True)
    owner_type = fields.String(
        required=True,
        validate=validate.OneOf(['individual', 'company'])
    )
    doublage = fields.Bool()


class RefDriverSchema(Schema):
    professional_licence = fields.String(required=True, allow_none=False)
    departement = fields.String(attribute='departement.numero')


class VehicleSchema(Schema):
    model = fields.String(required=False, allow_none=True)
    constructor = fields.String(required=False, allow_none=True)
    color = fields.String(required=False, allow_none=True)
    licence_plate = fields.String(required=True, allow_none=False)
    nb_seats = fields.Int(required=False, allow_none=True)
    characteristics = fields.List(fields.String, required=False, allow_none=False)
    type = fields.String(required=False, allow_none=True)
    cpam_conventionne = fields.Bool(required=False, allow_none=True)
    engine = fields.String(required=False, allow_none=True)


class PositionSchema(Schema):
    lon = fields.Float(required=True, allow_none=True)
    lat = fields.Float(required=True, allow_none=True)


class ListTaxisQueryStringSchema(Schema):
    """Schema for querystring arguments of GET /taxis."""
    class Meta:
        """Allow and discard unknown fields."""
        unknown = EXCLUDE

    lon = fields.Float(required=True)
    lat = fields.Float(required=True)
    favorite_operator = fields.String()
    count = fields.Int(validate=validate.Range(min=1, max=50))


class TaxiSchema(Schema):
    id = fields.String()
    internal_id = fields.String(allow_none=True)
    operator = fields.String(required=False, allow_none=False)
    vehicle = fields.Nested(VehicleSchema, required=True)
    ads = fields.Nested(RefADSSchema, required=True)
    driver = fields.Nested(RefDriverSchema, required=True)
    rating = fields.Float(required=False, allow_none=False)

    status = fields.String(
        required=False, allow_none=False,
        validate=validate.OneOf(UPDATABLE_VEHICLE_STATUS)
    )

    last_update = fields.Constant(None, required=False, allow_none=False)

    position = fields.Nested(PositionSchema, required=False, allow_none=False)

    crowfly_distance = fields.Constant(None, required=False, allow_none=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vehicle_description = None
        self.redis_location = None

    def dump(self, obj, *args, **kwargs):
        """This function should be called with a list of tuples of two or three
        elements. The first element is the taxi object to dump. Since a taxi
        can have several VehicleDescription (one for each operator), the second
        element should be the description to dump. The third optional element
        is the location used to display the crowlfy distance between the API
        caller and the taxi.
        """
        try:
            taxi, self.vehicle_description, self.redis_location = obj
        except ValueError:
            taxi, self.vehicle_description = obj

        return super().dump(taxi, *args, **kwargs)

    @decorators.post_dump(pass_original=True)
    def _add_fields(self, data, taxi, many=False):
        """Extend output with vehicle_description details, and position
        from redis.
        """
        assert self.vehicle_description

        taxi_redis = redis_backend.get_taxi(taxi.id, taxi.added_by.email)

        data.update({
            'operator': self.vehicle_description.added_by.email,
            'internal_id': self.vehicle_description.internal_id,
            'status': self.vehicle_description.status,
            # last_update is the last time location has been updated by
            # geotaxi.
            'last_update': taxi_redis.timestamp if taxi_redis else None,
            'position': {
                'lon': taxi_redis.lon if taxi_redis else None,
                'lat': taxi_redis.lat if taxi_redis else None,
            },
            'crowfly_distance': self.redis_location.distance if self.redis_location else None
        })
        data['vehicle'].update({
            'model': self.vehicle_description.model.name
                if self.vehicle_description.model else None,
            'constructor': self.vehicle_description.constructor.name
                if self.vehicle_description.constructor else None,
            'color': self.vehicle_description.color,
            'nb_seats': self.vehicle_description.nb_seats,
            'characteristics': self.vehicle_description.characteristics,
            'type': self.vehicle_description.type,
            'cpam_conventionne': self.vehicle_description.cpam_conventionne,
            'engine': self.vehicle_description.engine,
        })
        return data


class UserPublicSchema(Schema):
    """Display public informations about users."""
    commercial_name = fields.String(data_key='name')


class UserPrivateSchema(Schema):
    """Display restricted informations, only available for administrators,
    about users."""
    email = fields.String()
    apikey = fields.String()


class CustomerSchema(Schema):
    moteur_id = fields.Int()
    reprieve_begin = fields.DateTime(allow_none=True)
    reprieve_end = fields.DateTime(allow_none=True)
    ban_begin = fields.DateTime(allow_none=True)
    ban_end = fields.DateTime(allow_none=True)

    def __init__(self, current_user):
        self.current_user = current_user
        super().__init__()

    @validates_schema
    def validate_moteur_id(self, data, **kwargs):
        """There are three cases to handle:

        1/ user is admin but not a moteur: moteur_id is required
        2/ user is admin and moteur: moteur_id is optional, and defaults to
           user's id
        3/ user is not admin: if provided, moteur_id must be equal to
           user's id
        """
        # Case 1:
        if (
            self.current_user.has_role('admin')
            and not self.current_user.has_role('moteur')
            and 'moteur_id' not in data
        ):
            raise ValidationError(
                'Missing data for required field.',
                'moteur_id'
            )

        # Case 2: nothing to do

        # Case 3:
        if (
            not self.current_user.has_role('admin')
            and 'moteur_id' in data
            and data['moteur_id'] != self.current_user.id
        ):
            raise ValidationError(
                'Invalid moteur_id. Should match your user id.',
                'moteur_id'
            )


def data_schema_wrapper(WrappedSchema):
    """All API endpoints expect requests and responses to be formed as:

    >>> {
    ...    "data": [{
    ...    }]
    ... }

    where data must always be present, and be a list of always one element.

    It's probably not the best API design ever (...) but we need to keep this
    behavior for backward-compatibility.

    This function takes a marshmallow Schema as argument, and returns a wrapper
    that ensures data is definedm and is a list of exactly one element.
    """
    class DataSchema(Schema):
        data = fields.List(fields.Nested(WrappedSchema), required=True)

        @validates('data')
        def validate_length(self, value):
            if len(value) != 1:
                raise ValidationError('data should be a list of one element.')

    return DataSchema
