from marshmallow import (
    EXCLUDE,
    fields,
    Schema,
    validate,
    validates,
    validates_schema,
    ValidationError,
)
from marshmallow.schema import SchemaMeta

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
    """When we make a reference to an existing ADS, only the fields numero and
    insee are required.

    Other fields can be provided, but they are ignored.
    """
    numero = fields.String(required=True, allow_none=False)
    insee = fields.String(required=True, allow_none=False)

    category = fields.String(required=False)
    vehicle_id = fields.Int(required=False)
    owner_name = fields.String(required=False)
    owner_type = fields.String(
        required=False,
        validate=validate.OneOf(['individual', 'company'])
    )
    doublage = fields.Bool(required=False)


class ADSSchema(RefADSSchema):
    """ADS creation require to provide all these fields."""
    category = fields.String(required=False)
    vehicle_id = fields.Int(allow_none=True)
    owner_name = fields.String(required=False)
    owner_type = fields.String(
        required=False,
        validate=validate.OneOf(['individual', 'company']),
        allow_none=True
    )
    doublage = fields.Bool(required=False, allow_none=True)


class RefDriverSchema(Schema):
    professional_licence = fields.String(required=True, allow_none=False)
    departement = fields.String(attribute='departement.numero', required=True)


class VehicleSchema(Schema):
    id = fields.Integer(dump_only=True, required=False, allow_none=False)

    licence_plate = fields.String(required=True, allow_none=False)

    model_year = fields.Integer(required=False, allow_none=True)
    engine = fields.String(required=False, allow_none=True)
    horse_power = fields.Float(required=False, allow_none=True)
    relais = fields.Bool(required=False, allow_none=True)
    horodateur = fields.String(required=False, allow_none=True)
    taximetre = fields.String(required=False, allow_none=True)
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

    def load(self, fields, *args, **kwargs):
        # For backward compatibility, "model" and "constructor" can be provided
        # as None but they are internally stored as empty strings
        if 'model' in fields and fields['model'] is None:
            fields['model'] = ''
        if 'constructor' in fields and fields['constructor'] is None:
            fields['constructor'] = ''

        return super().load(fields, *args, **kwargs)

    def dump(self, obj, *args, **kwargs):
        vehicle, vehicle_description = obj
        ret = super().dump(vehicle, *args, **kwargs)
        ret.update({
            'model_year': vehicle_description.model_year,
            'engine': vehicle_description.engine,
            'horse_power': vehicle_description.horse_power,
            'relais': vehicle_description.relais,
            'horodateur': vehicle_description.horodateur,
            'taximetre': vehicle_description.taximetre,
            'date_dernier_ct': vehicle_description.date_dernier_ct,
            'date_validite_ct': vehicle_description.date_validite_ct,
            'special_need_vehicle': vehicle_description.special_need_vehicle,
            'type_': vehicle_description.type,
            'luxury': vehicle_description.luxury,
            'credit_card_accepted': vehicle_description.credit_card_accepted,
            'nfc_cc_accepted': vehicle_description.nfc_cc_accepted,
            'amex_accepted': vehicle_description.amex_accepted,
            'bank_check_accepted': vehicle_description.bank_check_accepted,
            'fresh_drink': vehicle_description.fresh_drink,
            'dvd_player': vehicle_description.dvd_player,
            'tablet': vehicle_description.tablet,
            'wifi': vehicle_description.wifi,
            'baby_seat': vehicle_description.baby_seat,
            'bike_accepted': vehicle_description.bike_accepted,
            'pet_accepted': vehicle_description.pet_accepted,
            'air_con': vehicle_description.air_con,
            'electronic_toll': vehicle_description.electronic_toll,
            'gps': vehicle_description.gps,
            'cpam_conventionne': vehicle_description.cpam_conventionne,
            'every_destination': vehicle_description.every_destination,
            'color': vehicle_description.color,
            'nb_seats': vehicle_description.nb_seats,
            # Empty model or constructors are exposed as null fields.
            'model': vehicle_description.model or None,
            'constructor': vehicle_description.constructor or None,
        })
        return ret


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


class ZUPCSchema(Schema):
    zupc_id = fields.String()
    nom = fields.String()

    def dump(self, obj, *args, **kwargs):
        zupc, nb_active_taxis = obj
        ret = super().dump(zupc, *args, **kwargs)
        if nb_active_taxis is not None:
            ret['nb_active'] = nb_active_taxis
        return ret


class TaxiSchema(Schema):
    id = fields.String()
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

    def dump(self, obj, *args, **kwargs):
        """This function should be called with a list of tuples of two or three
        elements:

        * The taxi object to dump
        * Since a taxi can have several VehicleDescription (one for each
          operator), the second element should be the description to dump
        * Optionally, a `redis_backend.Location` object to display the taxi
          location and the crowlfy distance between the API caller and the
          taxi."""
        try:
            taxi, vehicle_description, redis_location = obj
        except ValueError:
            taxi, vehicle_description = obj
            redis_location = None

        ret = super().dump(taxi, *args, **kwargs)

        # Add fields from vehicle_description and redis_location
        ret.update({
            'operator': vehicle_description.added_by.email,
            'status': vehicle_description.status,
            # last_update is the last time location has been updated by
            # geotaxi.
            'last_update': int(redis_location.update_date.timestamp()) if redis_location else None,
            'position': {
                'lon': redis_location.lon if redis_location else None,
                'lat': redis_location.lat if redis_location else None,
            },
            'crowfly_distance': redis_location.distance if redis_location else None
        })
        ret['vehicle'].update({
            'model': vehicle_description.model or None,
            'constructor': vehicle_description.constructor or None,
            'color': vehicle_description.color,
            'nb_seats': vehicle_description.nb_seats,
            'characteristics': vehicle_description.characteristics,
            'type': vehicle_description.type,
            'cpam_conventionne': vehicle_description.cpam_conventionne,
            'engine': vehicle_description.engine,
        })
        return ret


class TaxiPUTSchema(Schema):
    """PUT /taxis/:id accepts any field from TaxiSchema, but only the status is
    updated.

    This class is only used by apispec to render swagger documentation.
    """
    status = fields.String(
        required=False, allow_none=False,
        validate=validate.OneOf(UPDATABLE_VEHICLE_STATUS)
    )


class UserPublicSchema(Schema):
    """Display public informations about users."""
    commercial_name = fields.String(data_key='name')


class RoleSchema(Schema):
    name = fields.String()


class UserPrivateSchema(UserPublicSchema):
    """Display restricted informations about users. Should only be exposed to
    owners and administrators."""
    email = fields.String()
    apikey = fields.String()
    roles = fields.List(fields.Nested(RoleSchema))


class CustomerSchema(Schema):
    reprieve_begin = fields.DateTime(allow_none=True)
    reprieve_end = fields.DateTime(allow_none=True)
    ban_begin = fields.DateTime(allow_none=True)
    ban_end = fields.DateTime(allow_none=True)

    def __init__(self, current_user=None):
        self.current_user = current_user
        super().__init__()


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

    customer_lon = fields.Float(required=True)
    customer_lat = fields.Float(required=True)
    customer_address = fields.String(required=True)
    customer_phone_number = fields.String(required=True)
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
    session_id = fields.UUID(required=False, allow_none=True)
    operateur = fields.String(required=True, attribute='operateur.email')

    taxi_relation = fields.Nested(HailTaxiRelationSchema)
    taxi = fields.Nested(HailTaxiSchema)

    # For backward compatibility, taxi_id is not returned from GET
    # /hails/:id, but the field is required to create a taxi with POST
    # /hails/:id
    taxi_id = fields.String(required=True, load_only=True)

    creation_datetime = fields.DateTime()
    customer_id = fields.String(required=True)

    def dump(self, obj, *args, **kwargs):
        hail, taxi_position = obj
        ret = super().dump(hail, *args, **kwargs)

        # Taxi location should only be returned if the hail is in progress.
        if taxi_position and hail.status in (
            # Taxi accepted the request, customer can see the location while
            # taxi is coming or while the hail is ongoing.
            'accepted_by_taxi',
            'accepted_by_customer',
            'customer_on_board',
        ):
            ret['taxi']['position'] = {
                'lon': taxi_position.lon,
                'lat': taxi_position.lat
            }
            ret['taxi']['crowfly_distance'] = geodesic(
                (taxi_position.lat, taxi_position.lon),
                (hail.customer_lat, hail.customer_lon)
            ).kilometers
            ret['taxi']['last_update'] = taxi_position.timestamp
        # Don't display location for hails not in progress.
        else:
            ret['taxi']['position'] = {
                'lon': None,
                'lat': None
            }
            ret['taxi']['crowfly_distance'] = None
            ret['taxi']['last_update'] = None
        return ret


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


class ListZUPCQueryStringSchema(Schema):
    """Querystring arguments for GET /zupc."""
    lon = fields.Float(required=True)
    lat = fields.Float(required=True)


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

    class MCS(SchemaMeta):
        """DataSchema should have a different name for each contained type,
        otherwise apispec displays a warning.

        See https://github.com/marshmallow-code/apispec/issues/603"""
        __name__ = 'Data' + WrappedSchema.__class__.__name__

        def __init__(self, name, bases, attrs):
            return super().__init__(self.__name__, bases, attrs)

    class DataSchema(Schema, metaclass=MCS):
        data = fields.List(fields.Nested(WrappedSchema), required=True)

        if with_pagination:
            meta = fields.Nested(Pagination)

        @validates('data')
        def validate_length(self, value):
            if len(value) != 1:
                raise ValidationError('data should be a list of one element.')

    return DataSchema


#
# API request payloads and API responses are wrapped in an object with one key,
# "data", which is a list of exactly one element.
#
# In other words, for example:
#
# DriverSchema     = {'first_name': xx, 'last_name': yyy, ...}
# DataDriverSchema = {'data': [{'first_name': xx, 'last_name': yyy, ...}]}
#
DataADSSchema = data_schema_wrapper(ADSSchema())
DataCustomerSchema = data_schema_wrapper(CustomerSchema())
DataDriverSchema = data_schema_wrapper(DriverSchema())
DataTaxiSchema = data_schema_wrapper(TaxiSchema())
DataHailSchema = data_schema_wrapper(HailSchema())
DataHailListSchema = data_schema_wrapper(HailListSchema(), with_pagination=True)
DataUserPublicSchema = data_schema_wrapper(UserPublicSchema())
DataUserPrivateSchema = data_schema_wrapper(UserPrivateSchema())
DataVehicleSchema = data_schema_wrapper(VehicleSchema())
DataZUPCSchema = data_schema_wrapper(ZUPCSchema())
