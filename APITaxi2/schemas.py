import ipaddress
import socket
import urllib.parse

from flask import current_app

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

from APITaxi_models2 import (
    Hail,
    Town,
    ZUPC,
)
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


# Range to adjust the visibility of taxis to clients
TAXI_MIN_RADIUS = 150
TAXI_MAX_RADIUS = 500


class PageQueryStringMixin:
    """Used to accept a querystring param ?p, and make sure it is specified
    only once.
    """
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


class PositionMixin:
    """Used where a position is required."""
    lon = fields.Float(required=True, validate=validate.Range(min=-180, max=180))
    # The WGS84/EPSG:3857 spec says [-85.06,+85.06] but Redis only accepts
    # [-85.05112878, 85.05112878], so keep it
    lat = fields.Float(required=True, validate=validate.Range(min=-85.05112878, max=85.05112878))


class DepartementSchema(Schema):
    """Departement where the professional licence was issued."""
    nom = fields.String()
    numero = fields.String()

    @validates_schema
    def check_required(self, data, **kwargs):
        if 'nom' not in data and 'numero' not in data:
            raise ValidationError(
                'You need to specify at least "nom" or "numero"', 'nom'
            )


class DriverSchema(Schema):
    """Schema to create a driver"""
    first_name = fields.String(required=True)
    last_name = fields.String(required=True)
    birth_date = fields.Date(allow_none=True)
    professional_licence = fields.String(required=True, allow_none=False)
    departement = fields.Nested(DepartementSchema, required=True)


class RefTownSchema(Schema):
    """When we make a reference to an ADS, make the INSEE code more user-friendly."""
    name = fields.String(required=False)


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
    # Optional field translating the INSEE code to a town name
    town = fields.Nested(RefTownSchema, required=False, dump_only=True)


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
    """Reference to an existing driver"""
    professional_licence = fields.String(required=True, allow_none=False)
    departement = fields.String(attribute='departement.numero', required=True)
    first_name = fields.String(required=False)
    last_name = fields.String(required=False)


class VehicleSchema(Schema):
    """Schema to create a vehicle"""
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
        """For backward compatibility, string fields can be provided as "None"
        but they are internally stored as NOT NULL strings.
        """
        for field_name in (
            'model',
            'constructor',
            'engine',
            'horodateur',
            'taximetre',
            'color',
        ):
            if field_name in fields and fields[field_name] is None:
                fields[field_name] = ''

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
    """Reference to an existing vehicle"""

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
    # PositionMixin is not used as the position can be null
    lon = fields.Float(required=True, validate=validate.Range(min=-180, max=180), allow_none=True)
    lat = fields.Float(required=True, validate=validate.Range(min=-90, max=90), allow_none=True)


class ListTaxisQueryStringSchema(PositionMixin, Schema):
    """Schema for querystring arguments of GET /taxis."""
    class Meta:
        """Allow and discard unknown fields."""
        # TODO left for backwards compatibility with the map still using favorite_operator and count
        # finish to remove it when the map is merged into the console, search engines don't know about them
        unknown = EXCLUDE


class ZUPCSchema(Schema):
    """Response schema to list ZUPCs on the map"""
    zupc_id = fields.String()
    insee = fields.String()
    name = fields.String()
    type = fields.String()

    def dump(self, obj, *args, **kwargs):
        model, stats = obj
        ret = super().dump(model, *args, **kwargs)

        if isinstance(model, ZUPC):
            ret['type'] = 'ZUPC'
        elif isinstance(model, Town):
            ret['type'] = 'city'

        ret['stats'] = stats

        return ret


class ZUPCGeomSchema(Schema):
    """Represents a ZUPC and it's shape."""
    id = fields.String()
    nom = fields.String()
    geojson = fields.Raw()
    stats = fields.Raw()


class TownSchema(Schema):
    insee = fields.String()
    name = fields.String()


class TaxiSchema(Schema):
    """Schema to list, create, read or update taxis"""
    id = fields.String()
    added_at = fields.DateTime()
    operator = fields.String(required=False, allow_none=False)
    vehicle = fields.Nested(RefVehicleSchema, required=True)
    ads = fields.Nested(RefADSSchema, required=True)
    driver = fields.Nested(RefDriverSchema, required=True)
    rating = fields.Float(required=False, allow_none=False)

    status = fields.String(
        required=False, allow_none=False,
        validate=validate.OneOf(UPDATABLE_VEHICLE_STATUS)
    )
    # Adjustable visibility radius (if null, fallback to max radius)
    radius = fields.Integer(
        required=False, allow_none=True,
        validate=validate.Range(min=TAXI_MIN_RADIUS, max=TAXI_MAX_RADIUS)
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
            'radius': vehicle_description.radius,
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


class ListTaxisAllQuerystringSchema(Schema, PageQueryStringMixin):
    """Querystring arguments for GET /taxis/all."""
    id = fields.List(fields.String)
    licence_plate = fields.List(fields.String)


class TaxiPUTSchema(Schema):
    """PUT /taxis/:id accepts any field from TaxiSchema, but only the status is
    updated.

    This class is only used by apispec to render swagger documentation.
    """
    status = fields.String(
        required=False, allow_none=False,
        validate=validate.OneOf(UPDATABLE_VEHICLE_STATUS)
    )


class RoleSchema(Schema):
    """Reference to a role"""
    name = fields.String()


class ListUserQuerystringSchema(Schema, PageQueryStringMixin):
    """Querystring arguments for GET /users"""
    name = fields.List(fields.String)
    email = fields.List(fields.String)

    @validates_schema
    def check_lengths(self, data, **kwargs):
        if len(data.get('name', [])) > 1:
            raise ValidationError('Argument `name` should not be specified more than once')
        if len(data.get('email', [])) > 1:
            raise ValidationError('Argument `email` should not be specified more than once')


class ManagerSchema(Schema):
    """Reference to a manager"""
    id = fields.Int()
    commercial_name = fields.String(data_key='name')
    email = fields.String()


class UserSchema(Schema):
    """Display restricted informations about users. Should only be exposed to
    owners and administrators."""
    id = fields.Int()
    commercial_name = fields.String(data_key='name', allow_none=True)
    email = fields.String()
    apikey = fields.String()
    roles = fields.List(fields.Nested(RoleSchema))
    email_customer = fields.String(allow_none=True)
    email_technical = fields.String(allow_none=True)
    hail_endpoint_production = fields.String(allow_none=True)
    phone_number_customer = fields.String(allow_none=True)
    phone_number_technical = fields.String(allow_none=True)
    operator_api_key = fields.String(allow_none=True)
    operator_header_name = fields.String(allow_none=True)
    manager = fields.Nested(ManagerSchema, allow_none=True)

    managed = fields.Nested(
        'UserSchema',
        many=True,
        only=('id', 'email', 'commercial_name')
    )

    # User password can only be provided
    password = fields.String(load_only=True)

    @validates('password')
    def check_password(self, password):
        """Minimum is 8 chars if set, but empty values are also accepted."""
        if password:
            return validate.Length(min=8)(password)

    @validates('hail_endpoint_production')
    def check_endpoint(self, endpoint):
        """Reject internal and private addresses"""
        # Validate URL, except in development
        if endpoint and not current_app.debug:
            url = urllib.parse.urlparse(endpoint)
            if not url.hostname or url.scheme not in ('http', 'https'):
                raise ValidationError("This endpoint is invalid.")
            # Reject private IPs
            ip_address = ipaddress.ip_address(socket.gethostbyname(url.hostname))
            if ip_address.is_private:
                raise ValidationError("This endpoint is invalid.")


class CustomerSchema(Schema):
    """Schema to update customer"""
    reprieve_begin = fields.DateTime(allow_none=True)
    reprieve_end = fields.DateTime(allow_none=True)
    ban_begin = fields.DateTime(allow_none=True)
    ban_end = fields.DateTime(allow_none=True)

    def __init__(self, current_user=None):
        self.current_user = current_user
        super().__init__()


class HailTaxiRelationSchema(Schema):
    """Taxi rating is part of a "relation" subentry"""
    rating = fields.Float()


class HailTaxiSchema(Schema):
    """Reference to a taxi in a hail"""
    last_update = fields.Int()
    id = fields.String()
    position = fields.Nested(PositionSchema)
    crowfly_distance = fields.Float()


class HailSchema(Schema):
    """Schema to create read and update hails"""
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

    transitions = fields.Raw(attribute='transition_log')

    def dump(self, obj, *args, **kwargs):
        hail, taxi_position = obj
        ret = super().dump(hail, *args, **kwargs)

        # Taxi location should only be returned if the hail is in progress.
        if taxi_position and hail.status in (
            'emitted',
            'received',
            'sent_to_operator',
            'received_by_operator',
            'received_by_taxi',
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


class ListHailsQuerystringSchema(Schema, PageQueryStringMixin):
    """Querystring arguments for GET /hails/."""
    id = fields.List(fields.String)
    status = fields.List(fields.String(
        validate=validate.OneOf(Hail.status.property.columns[0].type.enums),
    ))
    operateur = fields.List(fields.String)
    moteur = fields.List(fields.String)
    taxi_id = fields.List(fields.String)
    date = fields.List(fields.Date('%Y/%m/%d'))
    customer_id = fields.List(fields.String)


class HailListSchema(Schema):
    """Response schema for GET /hails/"""
    id = fields.String()
    added_by = fields.String(attribute='added_by.email')
    operateur = fields.String(attribute='operateur.email')
    status = fields.String()
    creation_datetime = fields.DateTime()
    taxi_id = fields.String()
    customer_id = fields.String()


class HailBySessionUserSchema(Schema):
    """Reference to the operateur or moteur of a hail session"""
    id = fields.String()
    email = fields.String()
    commercial_name = fields.String()


class HailBySessionTaxiSchema(Schema):
    """Reference to the taxi of a hail session"""
    id = fields.String()


class HailBySessionSchema(Schema):
    """Reference to hails of the same session"""
    id = fields.String()
    status = fields.String()
    operateur = fields.Nested(HailBySessionUserSchema)
    moteur = fields.Nested(HailBySessionUserSchema)
    taxi = fields.Nested(HailBySessionTaxiSchema)
    added_at = fields.String()
    customer_lon = fields.Float()
    customer_lat = fields.Float()
    customer_address = fields.String()
    customer_phone_number = fields.String()
    taxi_phone_number = fields.String()
    initial_taxi_lat = fields.Float()
    initial_taxi_lon = fields.Float()


class HailBySessionListSchema(Schema):
    """Schema to list hails (grouped by session) in the console"""
    customer_id = fields.String()
    session_id = fields.String()
    added_by_id = fields.String()
    added_at = fields.DateTime()
    hails = fields.List(fields.Nested(HailBySessionSchema))


class ListHailsBySessionQuerystringSchema(Schema, PageQueryStringMixin):
    """Querystring arguments for GET /hails_by_session."""
    pass


class ListZUPCQueryStringSchema(PositionMixin, Schema):
    """Querystring arguments for GET /zupc."""
    pass


class ListTownQueryStringSchema(Schema):
    pass


class GeotaxiPositionSchema(PositionMixin, Schema):
    """Schema for a single unit of taxi coordinates."""
    taxi_id = fields.String(required=True)


class GeotaxiSchema(Schema):
    """Schema for the body of POST /geotaxi/"""
    positions = fields.Nested(GeotaxiPositionSchema, required=True, many=True)

    @validates('positions')
    def check_length(self, positions):
        """Reject the whole request if more than 50 positions are posted"""
        if len(positions) > 50:
            raise ValidationError('Up to 50 positions are accepted')


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
        per_page = fields.Int()
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
DataTaxiListSchema = data_schema_wrapper(TaxiSchema(), with_pagination=True)
DataHailSchema = data_schema_wrapper(HailSchema())
DataHailListSchema = data_schema_wrapper(HailListSchema(), with_pagination=True)
DataHailBySessionListSchema = data_schema_wrapper(HailBySessionListSchema(), with_pagination=True)
DataUserSchema = data_schema_wrapper(UserSchema())
DataUserListSchema = data_schema_wrapper(UserSchema(), with_pagination=True)
DataVehicleSchema = data_schema_wrapper(VehicleSchema())
DataZUPCSchema = data_schema_wrapper(ZUPCSchema())
DataZUPCGeomSchema = data_schema_wrapper(ZUPCGeomSchema())
DataGeotaxiSchema = data_schema_wrapper(GeotaxiSchema())
DataTownSchema = data_schema_wrapper(TownSchema())
