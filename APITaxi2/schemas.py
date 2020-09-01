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

from geopy.distance import geodesic

from APITaxi_models2 import Hail
from APITaxi_models2.hail import (
    INCIDENT_CUSTOMER_REASONS,
    INCIDENT_TAXI_REASONS,
    RATING_RIDE_REASONS,
    REPORTING_CUSTOMER_REASONS,
)
from APITaxi_models2.vehicle import (
    UPDATABLE_VEHICLE_STATUS,
    VehicleDescription,
)

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
    id = fields.Integer(dump_only=True, required=False, allow_none=False)

    licence_plate = fields.String(required=True, allow_none=False)

    internal_id = fields.String(allow_none=True)
    model_year = fields.Integer(required=False, allow_none=True)
    engine = fields.String(required=False, allow_none=True)
    horse_power = fields.Float(required=False, allow_none=True)
    relais = fields.Bool(required=False, allow_none=True)
    horodateur = fields.String(required=False, allow_none=True)
    taximetre = fields.String(requried=False, allow_none=True)
    date_dernier_ct = fields.Date(required=False, allow_none=True)
    date_validite_ct = fields.Date(required=False, allow_none=True)
    special_need_vehicle = fields.Bool(required=False, allow_none=True)
    type_ = fields.String(
        required=False, allow_none=True,
        validate=validate.OneOf(
            VehicleDescription.type.property.columns[0].type.enums
        )
    )
    luxury = fields.Bool(required=False, allow_none=True)
    credit_card_accepted = fields.Bool(required=False, allow_none=True)
    nfc_cc_accepted = fields.Bool(required=False, allow_none=True)
    amex_accepted = fields.Bool(required=False, allow_none=True)
    bank_check_accepted = fields.Bool(required=False, allow_none=True)
    fresh_drink = fields.Bool(required=False, allow_none=True)
    dvd_player = fields.Bool(required=False, allow_none=True)
    tablet = fields.Bool(required=False, allow_none=True)
    wifi = fields.Bool(required=False, allow_none=True)
    baby_seat = fields.Bool(required=False, allow_none=True)
    bike_accepted = fields.Bool(required=False, allow_none=True)
    pet_accepted = fields.Bool(required=False, allow_none=True)
    air_con = fields.Bool(required=False, allow_none=True)
    electronic_toll = fields.Bool(required=False, allow_none=True)
    gps = fields.Bool(required=False, allow_none=True)
    cpam_conventionne = fields.Bool(required=False, allow_none=True)
    every_destination = fields.Bool(required=False, allow_none=True)

    color = fields.String(required=False, allow_none=True)
    nb_seats = fields.Int(required=False, allow_none=True)
    model = fields.String(required=False, allow_none=True)
    constructor = fields.String(required=False, allow_none=True)

    def __init__(self, *args, **kwargs):
        self.vehicle_description = None
        return super().__init__(*args, **kwargs)

    def dump(self, obj, *args, **kwargs):
        vehicle, self.vehicle_description = obj
        return super().dump(vehicle, *args, **kwargs)

    @decorators.post_dump(pass_original=True)
    def _add_fields(self, data, vehicle, many=False):
        assert self.vehicle_description

        data.update({
            'internal_id': self.vehicle_description.internal_id,
            'model_year': self.vehicle_description.model_year,
            'engine': self.vehicle_description.engine,
            'horse_power': self.vehicle_description.horse_power,
            'relais': self.vehicle_description.relais,
            'horodateur': self.vehicle_description.horodateur,
            'taximetre': self.vehicle_description.taximetre,
            'date_dernier_ct': self.vehicle_description.date_dernier_ct,
            'date_validite_ct': self.vehicle_description.date_validite_ct,
            'special_need_vehicle': self.vehicle_description.special_need_vehicle,
            'type_': self.vehicle_description.type,
            'luxury': self.vehicle_description.luxury,
            'credit_card_accepted': self.vehicle_description.credit_card_accepted,
            'nfc_cc_accepted': self.vehicle_description.nfc_cc_accepted,
            'amex_accepted': self.vehicle_description.amex_accepted,
            'bank_check_accepted': self.vehicle_description.bank_check_accepted,
            'fresh_drink': self.vehicle_description.fresh_drink,
            'dvd_player': self.vehicle_description.dvd_player,
            'tablet': self.vehicle_description.tablet,
            'wifi': self.vehicle_description.wifi,
            'baby_seat': self.vehicle_description.baby_seat,
            'bike_accepted': self.vehicle_description.bike_accepted,
            'pet_accepted': self.vehicle_description.pet_accepted,
            'air_con': self.vehicle_description.air_con,
            'electronic_toll': self.vehicle_description.electronic_toll,
            'gps': self.vehicle_description.gps,
            'cpam_conventionne': self.vehicle_description.cpam_conventionne,
            'every_destination': self.vehicle_description.every_destination,
            'color': self.vehicle_description.color,
            'nb_seats': self.vehicle_description.nb_seats,
            'model': self.vehicle_description.model.name
                if self.vehicle_description.model else None,
            'constructor': self.vehicle_description.constructor.name
                if self.vehicle_description.constructor else None,
        })

        return data


class RefVehicleSchema(Schema):
    class Meta:
        """Allow and discard unknown fields."""
        unknown = EXCLUDE

    licence_plate = fields.String(required=True, allow_none=False)
    constructor = fields.String(required=False, allow_none=True)
    color = fields.String(required=False, allow_none=True)
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
    vehicle = fields.Nested(RefVehicleSchema, required=True)
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


class HailTaxiRelationSchema(Schema):
    rating = fields.Float()


class HailTaxiSchema(Schema):
    last_update = fields.Int()
    id = fields.String()
    position = fields.Nested(PositionSchema)
    crowfly_distance = fields.Float()


class HailSchema(Schema):
    id = fields.String()
    status = fields.String(
        validate=validate.OneOf(Hail.status.property.columns[0].type.enums),
    )
    taxi_phone_number = fields.String()

    customer_lon = fields.Float()
    customer_lat = fields.Float()
    customer_address = fields.String()
    customer_phone_number = fields.String()
    last_status_change = fields.DateTime()
    rating_ride = fields.Int(allow_none=True)
    rating_ride_reason = fields.String(
        validate=validate.OneOf(RATING_RIDE_REASONS),
        allow_none=True
    )
    incident_customer_reason = fields.String(
        validate=validate.OneOf(INCIDENT_CUSTOMER_REASONS),
        allow_none=True
    )
    incident_taxi_reason = fields.String(
        validate=validate.OneOf(INCIDENT_TAXI_REASONS),
        allow_none=True
    )
    reporting_customer = fields.Bool(allow_none=True)
    reporting_customer_reason = fields.String(
        validate=validate.OneOf(REPORTING_CUSTOMER_REASONS),
        allow_none=True
    )
    session_id = fields.String()
    operateur = fields.String(attribute='operateur.email')

    taxi_relation = fields.Nested(HailTaxiRelationSchema)
    taxi = fields.Nested(HailTaxiSchema)

    creation_datetime = fields.DateTime()
    customer_id = fields.String()

    def __init__(self, *args, **kwargs):
        self.taxi_position = None
        return super().__init__(*args, **kwargs)

    def dump(self, obj, *args, **kwargs):
        hail, self.taxi_position = obj
        return super().dump(hail, *args, **kwargs)

    @decorators.post_dump(pass_original=True)
    def _add_fields(self, data, hail, many=False):
        # Taxi location should only be returned if the hail is in progress.
        if self.taxi_position and hail.status in (
            'accepted_by_taxi',
            'accepted_by_customer',
            'customer_on_board',
        ):
            data['taxi']['position'] = {
                'lon': self.taxi_position.lon,
                'lat': self.taxi_position.lat
            }
            data['taxi']['crowfly_distance'] = geodesic(
                (self.taxi_position.lat, self.taxi_position.lon),
                (hail.customer_lat, hail.customer_lon)
            ).kilometers
            data['taxi']['last_update'] = self.taxi_position.timestamp
        # Don't display location for hails not in progress.
        else:
            data['taxi']['position'] = {
                'lon': None,
                'lat': None
            }
            data['taxi']['crowfly_distance'] = None
            data['taxi']['last_update'] = None
        return data


class ListHailQuerystringSchema(Schema):
    """Querystring arguments for GET /hails/."""
    status = fields.List(fields.String(
        validate=validate.OneOf(Hail.status.property.columns[0].type.enums),
    ))
    operateur = fields.List(fields.String)
    moteur = fields.List(fields.String)
    taxi_id = fields.List(fields.String)
    date = fields.List(fields.Date('%Y/%m/%d'))
    p = fields.List(fields.Int())

    @validates('p')
    def check_length(self, pages):
        """Querystring ?p can be only specified zero or one time, not more.

        Valid:   xxx?
        Valid:   xxx?p=1
        Invalid: xxx?p=1&p=2
        """
        if len(pages) != 1:
            raise ValidationError('Argument `p` is specified more than once')


class HailListSchema(Schema):
    id = fields.String()
    added_by = fields.String(attribute='added_by.email')
    operateur = fields.String(attribute='operateur.email')
    status = fields.String()
    creation_datetime = fields.DateTime()
    taxi_id = fields.String()


def data_schema_wrapper(WrappedSchema, with_pagination=False):
    """All API endpoints expect requests and responses to be formed as:

    >>> {
    ...    "data": [{
    ...    }]
    ... }

    where data must always be present, and be a list of always one element.

    It's probably not the best API design ever (...) but we need to keep this
    behavior for backward-compatibility.

    This function takes a marshmallow Schema as argument, and returns a wrapper
    that ensures data is defined and is a list of exactly one element.

    If with_pagination is True, a "meta" argument is added with pagination
    metadata. To use it, given a flask-sqlalchemy query:

    >>> query = query.paginate(page=1, per_page=20)
    >>> schema = data_schema_wrapper(MySchema, with_pagination=True)()
    >>> schema.dump({
    ...   'data': query.items,  # query.items is the list of objects paginated
    ...   'meta': query         # query is a Flask-SQLAlchemy Pagination object, with the fields
    ...                         # "next_num", "prev_num", "pages" and "total"
    ... })
    """
    class Pagination(Schema):
        next_page = fields.Int(attribute='next_num')
        prev_page = fields.Int(attribute='prev_num')
        pages = fields.Int()
        total = fields.Int()

    class DataSchema(Schema):
        data = fields.List(fields.Nested(WrappedSchema), required=True)

        if with_pagination:
            meta = fields.Nested(Pagination)

        @validates('data')
        def validate_length(self, value):
            if len(value) != 1:
                raise ValidationError('data should be a list of one element.')

    return DataSchema
