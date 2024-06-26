import http.client
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

from .security import current_user


# Range to adjust the visibility of taxis to clients
TAXI_MIN_RADIUS = 150
TAXI_MAX_RADIUS = 500

# Consider taxis on a neutral basis for clients
NEUTRAL_OPERATOR = "chauffeur professionnel"

NOT_EMPTY = validate.Length(min=1, error="Field may not be empty.")


def hide_phone_numbers(ret):
    if ret['status'] != 'accepted_by_customer':
        is_admin = current_user.has_role('admin') if current_user else None
        if not is_admin:
            ret['taxi_phone_number'] = "0600000000"
            ret['customer_phone_number'] = "0600000000"


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
    # [-85.05112878, 85.05112878], so keep it, doesn't affect France bounding box
    lat = fields.Float(required=True, validate=validate.Range(min=-85.05112878, max=85.05112878))


class DepartementSchema(Schema):
    """Departement where the professional licence was issued."""
    nom = fields.String(metadata={'deprecated': True})
    numero = fields.String()

    @validates_schema
    def check_required(self, data, **kwargs):
        if 'nom' not in data and 'numero' not in data:
            raise ValidationError(
                'You need to specify at least "nom" or "numero"', 'nom'
            )


class DriverSchema(Schema):
    """Schema to create a driver"""
    first_name = fields.String(required=True, metadata={
        'description': "prénom du conducteur",
    })
    last_name = fields.String(required=True, metadata={
        'description': "nom du conducteur",
    })
    birth_date = fields.Date(allow_none=True, metadata={
        'description': "date de naissance du conducteur",
    })
    professional_licence = fields.String(
        required=True, allow_none=False, validate=NOT_EMPTY, metadata={
            'description': "n° carte professionnelle",
        }
    )
    departement = fields.Nested(DepartementSchema, required=True, metadata={
        'description': "département de délivrance de la carte professionnelle",
    })


class RefTownSchema(Schema):
    """When we make a reference to an ADS, make the INSEE code more user-friendly."""
    name = fields.String(required=False)


class RefADSSchema(Schema):
    """Representation of an ADS attached to a taxi.

    When the taxi is created, only the fields numero and insee are required.
    Other fields can be provided, but they are ignored.
    """

    class Meta:
        """Allow and discard unknown fields, short path to preserve BC."""
        unknown = EXCLUDE

    # Required to create a taxi
    numero = fields.String(
        required=True, allow_none=False, validate=NOT_EMPTY,
    )
    insee = fields.String(required=True, allow_none=False)

    # Exposed on reading a taxi
    vehicle_id = fields.Int(dump_only=True)
    owner_name = fields.String(dump_only=True)
    owner_type = fields.String(dump_only=True)
    doublage = fields.Bool(dump_only=True)

    # Subfield translating the INSEE code to a town name on a taxi GET
    town = fields.Nested(RefTownSchema, dump_only=True)

    # Obsolete but kept for backwards compatibility
    category = fields.Constant("", dump_only=True, metadata={'deprecated': True})


class ADSSchema(Schema):
    """ADS creation require to provide all these fields."""
    numero = fields.String(
        required=True, allow_none=False, validate=NOT_EMPTY, metadata={
            'description': "numéro attribué à l'ADS par l'autorité de délivrance",
        }
    )
    insee = fields.String(required=True, allow_none=False, metadata={
        'description': "code INSEE de la collectivité locale d'attribution",
    })
    vehicle_id = fields.Int(allow_none=True, metadata={
        'description': "identifiant du véhicule dans la DB",
    })
    owner_name = fields.String(required=False, metadata={
        'description': "nom ou raison sociale du titulaire de l'ADS",
    })
    owner_type = fields.String(
        required=False, validate=validate.OneOf(['individual', 'company']),
        allow_none=True, metadata={
            'description': "personne morale / personne physique/ NR"
        },
    )
    doublage = fields.Bool(required=False, allow_none=True, metadata={
        'description': "double sortie journalière autorisée",
    })

    # Obsolete but kept for backwards compatibility
    category = fields.String(required=False, metadata={'deprecated': True})


class RefDriverSchema(Schema):
    """Reference to an existing driver"""

    class Meta:
        """Allow and discard unknown fields, short path to preserve BC."""
        unknown = EXCLUDE

    # Required to create a taxi
    professional_licence = fields.String(
        required=True, allow_none=False, validate=NOT_EMPTY,
    )
    departement = fields.String(
        attribute='departement.numero', required=True, validate=validate.Length(min=2, max=3),
    )

    # Exposed on reading a taxi
    first_name = fields.String(dump_only=True)
    last_name = fields.String(dump_only=True)


class VehicleSchema(Schema):
    """Schema to read, create or update a vehicle"""
    id = fields.Integer(dump_only=True, required=False, allow_none=False)

    # required is not the same as not empty!
    # considering both the old and the new system, the bare minimum without any dash
    # or separator is 7, and the maximum with all the formatting is 10
    licence_plate = fields.String(
        required=True, allow_none=False, validate=validate.Length(min=7, max=10),
        metadata={'description': "numéro d'immatriculation du véhicule"},
    )

    # The vehicle itself
    model = fields.String(required=False, allow_none=True, metadata={
        'description': "modèle du véhicule",
    })
    constructor = fields.String(required=False, allow_none=True, metadata={
        'description': "constructeur du véhicule",
    })
    engine = fields.String(required=False, allow_none=True, metadata={
        'description': "motorisation (diesel, électrique...)",
    })
    color = fields.String(required=False, allow_none=True, metadata={
        'description': "couleur du véhicule",
    })
    nb_seats = fields.Int(required=False, allow_none=True, metadata={
        'description': "nombre de places",
    })
    relais = fields.Bool(
        required=False, allow_none=True, metadata={
            'description': "véhicule relais au sens de l'article R.3121-2 du code des transports",
        }
    )

    # Characteristics
    bank_check_accepted = fields.Bool(required=False, allow_none=True, metadata={
        'description': "chèques bancaires français acceptés",
    })
    baby_seat = fields.Bool(required=False, allow_none=True, metadata={
        'description': "siège bébé disponible",
    })
    bike_accepted = fields.Bool(required=False, allow_none=True, metadata={
        'description': "vélo accepté",
    })
    pet_accepted = fields.Bool(required=False, allow_none=True, metadata={
        'description': "animaux de compagnie acceptés",
    })
    amex_accepted = fields.Bool(required=False, allow_none=True, metadata={
        'description': "équipé American Express",
    })
    wifi = fields.Bool(required=False, allow_none=True, metadata={
        'description': "Wi-Fi à bord",
    })
    vasp_handicap = fields.Bool(required=False, allow_none=True, metadata={
        'description': "Catégorie VASP (J1) carrosserie handicap (J3) sur la carte grise",
    })

    # Obsolete but kept for backwards compatibility
    air_con = fields.Bool(required=False, allow_none=True, metadata={'deprecated': True})
    horodateur = fields.String(required=False, allow_none=True, metadata={'deprecated': True})
    date_dernier_ct = fields.Date(required=False, allow_none=True, metadata={'deprecated': True})
    date_validite_ct = fields.Date(required=False, allow_none=True, metadata={'deprecated': True})
    credit_card_accepted = fields.Bool(required=False, allow_none=True, metadata={'deprecated': True})
    electronic_toll = fields.Bool(required=False, allow_none=True, metadata={'deprecated': True})
    fresh_drink = fields.Bool(required=False, allow_none=True, metadata={'deprecated': True})
    tablet = fields.Bool(required=False, allow_none=True, metadata={'deprecated': True})
    dvd_player = fields.Bool(required=False, allow_none=True, metadata={'deprecated': True})
    taximetre = fields.String(required=False, allow_none=True, metadata={'deprecated': True})
    every_destination = fields.Bool(required=False, allow_none=True, metadata={'deprecated': True})
    nfc_cc_accepted = fields.Bool(required=False, allow_none=True, metadata={'deprecated': True})
    special_need_vehicle = fields.Bool(required=False, allow_none=True, metadata={'deprecated': True})
    gps = fields.Bool(required=False, allow_none=True, metadata={'deprecated': True})
    luxury = fields.Bool(required=False, allow_none=True, metadata={'deprecated': True})
    horse_power = fields.Float(required=False, allow_none=True, metadata={'deprecated': True})
    model_year = fields.Integer(required=False, allow_none=True, metadata={'deprecated': True})
    type_ = fields.String(
        required=False, allow_none=True,
        validate=validate.OneOf(
            VehicleDescription.type.property.columns[0].type.enums
        ), metadata={'deprecated': True}
    )
    cpam_conventionne = fields.Bool(required=False, allow_none=True, metadata={'deprecated': True})

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
            # Empty model or constructors are exposed as null fields.
            'model': vehicle_description.model or None,
            'constructor': vehicle_description.constructor or None,
            'engine': vehicle_description.engine,
            'color': vehicle_description.color,
            'nb_seats': vehicle_description.nb_seats,
            'relais': vehicle_description.relais,
            # Characteristics
            'bank_check_accepted': vehicle_description.bank_check_accepted,
            'baby_seat': vehicle_description.baby_seat,
            'bike_accepted': vehicle_description.bike_accepted,
            'pet_accepted': vehicle_description.pet_accepted,
            'amex_accepted': vehicle_description.amex_accepted,
            'wifi': vehicle_description.wifi,
            'vasp_handicap': vehicle_description.vasp_handicap,
        })
        return ret


class RefVehicleSchema(Schema):
    """Representation of a vehicle attached to a taxi."""

    class Meta:
        """Allow and discard unknown fields, short path to preserve BC."""
        unknown = EXCLUDE

    # Required to create a taxi, and not empty!
    licence_plate = fields.String(
        required=True, allow_none=False, validate=validate.Length(min=7, max=10)
    )

    # Exposed on reading a taxi
    constructor = fields.String(dump_only=True)
    color = fields.String(dump_only=True)
    nb_seats = fields.Int(dump_only=True)
    characteristics = fields.List(fields.String, dump_only=True)
    engine = fields.String(dump_only=True)

    # Obsolete but kept for backwards compatibility
    type = fields.String(dump_only=True, metadata={'deprecated': True})
    cpam_conventionne = fields.Bool(dump_only=True, metadata={'deprecated': True})


class TaxiPositionSchema(Schema):
    """Representation of taxi position from Redis, so read only."""
    lon = fields.Float(allow_none=True, dump_only=True)
    lat = fields.Float(allow_none=True, dump_only=True)


class ListTaxisQueryStringSchema(PositionMixin, Schema):
    """Schema for querystring arguments of GET /taxis."""
    class Meta:
        """Allow and discard unknown fields."""
        # TODO left for backwards compatibility with partners who still use them
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
    """Represents a ZUPC and its shape."""
    id = fields.String()
    nom = fields.String()
    geojson = fields.Raw()
    stats = fields.Raw()


class TownSchema(Schema):
    insee = fields.String()
    name = fields.String()


class TaxiSchema(Schema):
    """Schema to list, create, read or update taxis"""

    class Meta:
        """Allow and discard unknown fields, short path to preserve BC."""
        unknown = EXCLUDE

    # Required to create a taxi
    vehicle = fields.Nested(RefVehicleSchema, required=True)
    ads = fields.Nested(RefADSSchema, required=True)
    driver = fields.Nested(RefDriverSchema, required=True)

    # Exposed on reading a taxi
    id = fields.String(dump_only=True)
    added_at = fields.DateTime(dump_only=True)
    operator = fields.String(dump_only=True)

    # Obsolete but kept for backwards compatibility
    rating = fields.Float(required=False, allow_none=False, metadata={'deprecated': True})

    status = fields.String(
        required=False, allow_none=False,
        validate=validate.OneOf(UPDATABLE_VEHICLE_STATUS)
    )
    # Adjustable visibility radius (if null, fallback to max radius)
    radius = fields.Integer(
        required=False, allow_none=True,
        validate=validate.Range(min=TAXI_MIN_RADIUS, max=TAXI_MAX_RADIUS)
    )

    # Provided by Redis
    last_update = fields.Int(allow_none=True, dump_only=True)
    position = fields.Nested(TaxiPositionSchema, dump_only=True)
    crowfly_distance = fields.Float(allow_none=True, dump_only=True)

    def dump(self, obj, *args, **kwargs):
        """This function should be called with a list of tuples of two (create)
        or three (read, update) elements:

        * The taxi object to dump
        * Since a taxi can have several VehicleDescription (one for each
          operator), the second element should be the description to dump
        * Optionally, a `redis_backend.Location` object to display the taxi
          location and the crowfly distance between the API caller and the
          taxi.
        """
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


class SearchVehicleSchema(Schema):
    """Describe a vehicle when searching at taxi"""

    model = fields.String()
    constructor = fields.String()
    nb_seats = fields.Int()
    engine = fields.String()
    characteristics = fields.List(fields.String)

    # Only shared after the hail was accepted (see HailVehicleSchema)
    licence_plate = fields.Constant("", metadata={'deprecated': True})
    color = fields.String(metadata={'deprecated': True})

    # Obsolete but kept for backwards compatibility
    type = fields.Constant("normal", metadata={'deprecated': True})
    cpam_conventionne = fields.Constant(None, metadata={'deprecated': True, 'description': "always null, kept for compatibility"})


class SearchTaxiSchema(Schema):
    """Fork of the full taxi schema with only the parts required for client apps."""
    id = fields.String()
    operator = fields.Constant(NEUTRAL_OPERATOR, metadata={
        'description': f'Retourne toujours "${NEUTRAL_OPERATOR}"',
    })  # Kept as needed to POST a hail request
    crowfly_distance = fields.Float()  # Kept, already computed anyway
    position = fields.Nested(TaxiPositionSchema)
    vehicle = fields.Nested(SearchVehicleSchema)

    # Obsolete but kept for backwards compatibility
    rating = fields.Constant(0, metadata={'deprecated': True})
    status = fields.Constant("free", metadata={'deprecated': True})
    radius = fields.Constant(0, metadata={'deprecated': True})
    last_update = fields.Constant(None, metadata={'deprecated': True})
    added_at = fields.Constant("1970-01-01T00:00:00", metadata={'deprecated': True})

    def dump(self, obj, *args, **kwargs):
        """This function should be called with a list of tuples of three
        elements:

        * the taxi object to dump
        * since a taxi can have several VehicleDescription (one for each
          operator), the second element should be the description to dump
        * a `redis_backend.Location` object to display the taxi
          location and the crowfly distance between the API caller and the
          taxi.
        """
        try:
            taxi, vehicle_description, redis_location = obj
        except ValueError:
            taxi, vehicle_description = obj
            redis_location = None

        ret = super().dump(taxi, *args, **kwargs)

        # Add fields for backwards compatibility, but to remove ASAP
        ret.update({
            "ads": {
                "vehicle_id": 0,
                "insee": "",
                "owner_type": "",
                "doublage": None,
                "town": {
                    "name": ""
                },
                "owner_name": "",
                "category": "",
                "numero": "",
            },
            "driver": {
                "professional_licence": "",
                "first_name": "",
                "last_name": "",
                "departement": ""
            },
        })

        # Add fields from vehicle_description and redis_location
        ret.update({
            'operator': vehicle_description.added_by.email,
            'position': {
                'lon': redis_location.lon if redis_location else None,
                'lat': redis_location.lat if redis_location else None,
            },
            'crowfly_distance': redis_location.distance if redis_location else None
        })
        ret['vehicle'].update({
            'model': vehicle_description.model or None,
            'constructor': vehicle_description.constructor or None,
            'nb_seats': vehicle_description.nb_seats,
            'engine': vehicle_description.engine,
            'characteristics': vehicle_description.characteristics,
            # Moved to HailVehicleSchema
            'color': "",
            # Needed for tracing down issues
            'licence_plate': taxi.vehicle.licence_plate if current_user and current_user.has_role('admin') else "",
        })

        # Don't expose the real taxi ID to the customer
        if current_app.config.get('FAKE_TAXI_ID'):
            if current_user and not current_user.has_role('admin'):
                # Don't hide when our virtual operator is involved, we'll need this for the simulator
                if current_user.email != current_app.config.get('INTEGRATION_ACCOUNT_EMAIL'):
                    ret['id'] = taxi.fake_taxi_id

        # Consider taxis on a neutral basis for clients, including when the partner is both moteur and operateur
        # but keep the information for the admin console
        if current_app.config.get('NEUTRAL_OPERATOR'):
            if current_user and not current_user.has_role('admin'):
                # We still need to tell our virtual operator apart
                if ret['operator'] == current_app.config.get('INTEGRATION_ACCOUNT_EMAIL'):
                    ret['driver']['professional_licence'] = "integration"
                ret['operator'] = NEUTRAL_OPERATOR

        return ret


class ListTaxisAllQuerystringSchema(Schema, PageQueryStringMixin):
    """Querystring arguments for GET /taxis/all."""
    id = fields.List(fields.String)
    licence_plate = fields.List(fields.String)


class CreateTaxiSchema(Schema):
    """POST /taxis only accepts references to vehicle, ADS, driver to bind them together.

    This class is only used by apispec to render swagger documentation.
    """
    vehicle = fields.Nested(RefVehicleSchema, required=True)
    ads = fields.Nested(RefADSSchema, required=True)
    driver = fields.Nested(RefDriverSchema, required=True)


class TaxiDetailsSchema(Schema):
    """PUT /taxis/:id accepts any field from TaxiSchema, but only the status
    and radius are updated.

    This class is only used by apispec to render swagger documentation.
    """
    status = fields.String(
        required=False, allow_none=False,
        validate=validate.OneOf(UPDATABLE_VEHICLE_STATUS)
    )
    radius = fields.Integer(
        required=False, allow_none=True,
        validate=validate.Range(min=TAXI_MIN_RADIUS, max=TAXI_MAX_RADIUS)
    )


class RoleSchema(Schema):
    """Reference to a role"""
    name = fields.String()


class ListUserQuerystringSchema(Schema, PageQueryStringMixin):
    """Querystring arguments for GET /users"""
    name = fields.List(fields.String)
    email = fields.List(fields.String)
    manager = fields.List(fields.String)
    role = fields.List(fields.String)

    @validates_schema
    def check_lengths(self, data, **kwargs):
        for field in ('name', 'email', 'manager', 'role'):
            if len(data.get(field, [])) > 1:
                raise ValidationError(f'Argument `{field}` should not be specified more than once')


class ManagerSchema(Schema):
    """Reference to a manager"""
    id = fields.Int()
    commercial_name = fields.String(data_key='name')
    email = fields.String()


def validate_header_name(value):
    if not value:
        return
    try:
        if not http.client._is_legal_header_name(value.encode('ascii')):
            raise ValidationError('Invalid header name')
    except UnicodeEncodeError:
        raise ValidationError('Invalid header name')
    return value


def validate_header_value(value):
    try:
        if http.client._is_illegal_header_value(value.encode('ascii')):
            raise ValidationError('Invalid header value')
    except UnicodeEncodeError:
        raise ValidationError('Invalid header value')
    return value


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
    operator_api_key = fields.String(  # operator header value
        allow_none=True, validate=validate_header_value,
    )
    operator_header_name = fields.String(
        allow_none=True, validate=validate_header_name,
    )
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
            try:
                ip_address = ipaddress.ip_address(socket.gethostbyname(url.hostname))
            except OSError:
                raise ValidationError("This URL could not be resolved.")
            else:
                if ip_address.is_private:
                    raise ValidationError("This endpoint is invalid.")


class CustomerSchema(Schema):
    """Schema to update customer"""
    reprieve_begin = fields.DateTime(allow_none=True, metadata={'deprecated': True})
    reprieve_end = fields.DateTime(allow_none=True, metadata={'deprecated': True})
    ban_begin = fields.DateTime(allow_none=True)
    ban_end = fields.DateTime(allow_none=True)

    def __init__(self, current_user=None):
        self.current_user = current_user
        super().__init__()


class HailTaxiRelationSchema(Schema):
    """Taxi rating is part of a "relation" subentry"""
    rating = fields.Float(metadata={'deprecated': True})


class CreateHailSchema(Schema):
    """Schema with only the required fields to create hails."""
    customer_lon = fields.Float(
        required=True, validate=validate.Range(min=-180, max=180)
    )
    customer_lat = fields.Float(
        # See PositionMixin comment
        required=True, validate=validate.Range(min=-85.05112878, max=85.05112878)
    )
    customer_address = fields.String(required=True)
    customer_phone_number = fields.String(required=True)
    customer_id = fields.String(required=True)

    # Both required to identify which taxi was picked
    taxi_id = fields.String(required=True)
    operateur = fields.String(required=False, attribute='operateur.email')

    # Optional session ID when multiple hails are made
    session_id = fields.UUID(required=False, allow_none=True)


class HailVehicleSchema(Schema):
    """Reference to a vehicle in a hail.

    Added to share more information for the customer to identify the vehicle incoming.
    """
    licence_plate = fields.String(dump_only=True)
    color = fields.String(dump_only=True)
    nb_seats = fields.Int(dump_only=True)
    characteristics = fields.List(fields.String, dump_only=True)


class HailDriverSchema(Schema):
    """Reference to a driver in a hail.

    Added to share more information for the customer to identify the vehicle incoming.
    """
    first_name = fields.String(dump_only=True)
    last_name = fields.String(dump_only=True)


class HailTaxiSchema(Schema):
    """Reference to a taxi in a hail"""
    last_update = fields.Int(dump_only=True)
    id = fields.String(dump_only=True)
    position = fields.Nested(TaxiPositionSchema, dump_only=True)
    crowfly_distance = fields.Float(dump_only=True)
    vehicle = fields.Nested(HailVehicleSchema, dump_only=True)
    driver = fields.Nested(HailDriverSchema, dump_only=True)


class HailSchema(Schema):
    """Schema to read and update hails."""
    id = fields.String(dump_only=True)
    session_id = fields.UUID(dump_only=True)
    operateur = fields.String(dump_only=True, attribute='operateur.email')
    taxi = fields.Nested(HailTaxiSchema, dump_only=True)
    customer_id = fields.String(dump_only=True)
    creation_datetime = fields.DateTime(dump_only=True)
    last_status_change = fields.DateTime(dump_only=True)
    transitions = fields.Raw(
        attribute='transition_log', dump_only=True,
        metadata={'type': 'array', 'items': {'type': 'object'}, 'description': "events for debug purposes, not part of the API"},
    )

    # Can be changed by both parties
    status = fields.String(
        validate=validate.OneOf(Hail.status.property.columns[0].type.enums),
        metadata={'description': "operator, client"},
    )

    # Can be changed by the operateur
    taxi_phone_number = fields.String(metadata={'description': "operator"})
    incident_taxi_reason = fields.String(
        validate=validate.OneOf(INCIDENT_TAXI_REASONS),
        allow_none=True, metadata={'description': "operator"},
    )
    reporting_customer = fields.Bool(allow_none=True, metadata={'description': "operator"})
    reporting_customer_reason = fields.String(
        validate=validate.OneOf(REPORTING_CUSTOMER_REASONS),
        allow_none=True, metadata={'description': "operator"},
    )

    # Can be changed by the moteur
    customer_lon = fields.Float(
        validate=validate.Range(min=-180, max=180), metadata={'description': "client"},
    )
    customer_lat = fields.Float(
        # See PositionMixin comment
        validate=validate.Range(min=-85.05112878, max=85.05112878), metadata={'description': "client"},
    )
    customer_address = fields.String(metadata={'description': "client"})
    customer_phone_number = fields.String(metadata={'description': "client"})
    incident_customer_reason = fields.String(
        validate=validate.OneOf(INCIDENT_CUSTOMER_REASONS),
        allow_none=True, metadata={'description': "client"},
    )
    # Obsolete but kept for backwards compatibility
    taxi_relation = fields.Nested(HailTaxiRelationSchema, dump_only=True, metadata={'deprecated': True})
    rating_ride = fields.Int(allow_none=True, metadata={'deprecated': True})
    rating_ride_reason = fields.String(
        validate=validate.OneOf(RATING_RIDE_REASONS),
        allow_none=True, metadata={'deprecated': True},
    )

    def dump(self, obj, *args, **kwargs):
        hail, taxi_position, vehicle_description = obj
        ret = super().dump(hail, *args, **kwargs)

        # Taxi location should only be returned if the hail is in progress.
        if taxi_position and hail.status in (
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

        # Those were already given at the search step, but treated like an API change
        if vehicle_description and current_user and current_user.id in current_app.config.get('HAIL_TAXI_VEHICLE_DETAILS', []):
            ret['taxi']['vehicle']['nb_seats'] = vehicle_description.nb_seats
            ret['taxi']['vehicle']['characteristics'] = vehicle_description.characteristics
        # Those are more identifying, and require taxi approval
        if vehicle_description and hail.status in (
            'accepted_by_taxi',
            'accepted_by_customer',
            'customer_on_board',
        ):
            ret['taxi']['vehicle']['color'] = vehicle_description.color
        else:
            ret['taxi']['vehicle']['licence_plate'] = ""
            ret['taxi']['vehicle']['color'] = ""
            ret['taxi']['driver']['first_name'] = ""
            ret['taxi']['driver']['last_name'] = ""

        # The phone number is only needed when the two parties reach other
        hide_phone_numbers(ret)

        # Don't expose the real taxi ID to the customer
        if current_app.config.get('FAKE_TAXI_ID'):
            if current_user and not current_user.has_role('admin') and current_user.email != hail.operateur.email:
                # Don't hide when moteur is also the operateur of the taxi (I can't say which side requested)
                ret['taxi']['id'] = hail.fake_taxi_id

        # Consider taxis on a neutral basis for clients, but keep the information for the admins and the operator itself
        # which includes celery tasks where there is no current user when we send the hail request to the callback endpoint
        # so everyone but moteurs see the real operateur, including when an operateur+moteur is not the hail operateur itself
        if current_app.config.get('NEUTRAL_OPERATOR'):
            if current_user and not current_user.has_role('admin') and current_user.email != hail.operateur.email:
                # Don't hide when moteur is also the operateur of the taxi (I can't say which side requested)
                ret['operateur'] = NEUTRAL_OPERATOR

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

    def dump(self, obj, *args, **kwargs):
        ret = super().dump(obj, *args, **kwargs)

        # Don't expose the real taxi ID to the customer
        if current_app.config.get('FAKE_TAXI_ID'):
            if current_user and not current_user.has_role('admin') and current_user.email != obj.operateur.email:
                # Don't hide when moteur is also the operateur of the taxi (I can't say which side requested)
                ret['taxi_id'] = obj.fake_taxi_id

        # Consider taxis on a neutral basis for clients
        # but keep the information for the admins and the hail operator itself
        if current_app.config.get('NEUTRAL_OPERATOR'):
            if current_user and not current_user.has_role('admin') and current_user.email != obj.operateur.email:
                # Don't hide when moteur is also the operateur of the taxi (I can't say which side requested)
                ret['operateur'] = NEUTRAL_OPERATOR

        return ret


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

    def dump(self, obj, *args, **kwargs):
        ret = super().dump(obj, *args, **kwargs)

        # The phone number is only needed when the two parties reach other
        hide_phone_numbers(ret)

        # Don't expose the real taxi ID to the customer
        if current_app.config.get('FAKE_TAXI_ID'):
            if current_user and not current_user.has_role('admin') and current_user.email != obj['operateur']['email']:
                # Don't hide when moteur is also the operateur of the taxi (I can't say which side requested)
                ret['taxi']['id'] = obj['fake_taxi_id']

        # Consider taxis on a neutral basis for clients
        # but keep the information for the admins and the hail operator itself
        if current_app.config.get('NEUTRAL_OPERATOR'):
            if current_user and not current_user.has_role('admin') and current_user.email != obj['operateur']['email']:
                # Don't hide when moteur is also the operateur of the taxi (I can't say which side requested)
                ret['operateur']['email'] = NEUTRAL_OPERATOR
                ret['operateur']['commercial_name'] = NEUTRAL_OPERATOR

        return ret


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
    search = fields.String()


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


class StatsMilestones(Schema):
    today = fields.Integer()
    three_months_ago = fields.Integer()
    six_months_ago = fields.Integer()
    twelve_months_ago = fields.Integer()


class StatsTaxisSchema(Schema):
    registered_taxis = fields.Nested(StatsMilestones())
    connected_taxis = fields.Nested(StatsMilestones())
    registered_taxis_since_threshold = fields.Nested(StatsMilestones())
    connected_taxis_since_threshold = fields.Nested(StatsMilestones())
    connected_taxis_now = fields.Integer()
    monthly_hails_per_taxi = fields.Float()
    average_radius = fields.Float()
    average_radius_change = fields.Float()
    connected_taxis_per_hour = fields.Dict()


class StatsHailsTotal(Schema):
    current_year = fields.List(fields.List(fields.Int()))
    last_year = fields.List(fields.List(fields.Int()))


class StatsHailsAverageDetails(Schema):
    total = fields.Float()
    timeout_customer = fields.Float()
    declined_by_customer = fields.Float()
    incident_taxi = fields.Float()
    declined_by_taxi = fields.Float()


class StatsHailsAveragePeriods(Schema):
    daily = fields.Nested(StatsHailsAverageDetails())
    weekly = fields.Nested(StatsHailsAverageDetails())
    monthly = fields.Nested(StatsHailsAverageDetails())


class StatsHailsAverage(Schema):
    last_three_months = fields.Nested(StatsHailsAveragePeriods())
    current_year = fields.Nested(StatsHailsAveragePeriods())
    last_year = fields.Nested(StatsHailsAveragePeriods())


class StatsAverageTimes(Schema):
    accepted_by_taxi = fields.Float()
    accepted_by_customer = fields.Float()
    timeout_customer = fields.Float()
    declined_by_customer = fields.Float()
    timeout_taxi = fields.Float()
    incident_taxi = fields.Float()
    customer_on_board_incident_taxi = fields.Float()
    customer_on_board = fields.Float()


class StatsHailsSchema(Schema):
    hails_received = fields.Nested(StatsMilestones())
    hails_finished = fields.Nested(StatsMilestones())
    hails_declined_by_taxi = fields.Nested(StatsMilestones())
    hails_declined_by_customer = fields.Nested(StatsMilestones())
    hails_timeout_taxi = fields.Nested(StatsMilestones())
    hails_timeout_ride = fields.Nested(StatsMilestones())
    hails_timeout_customer = fields.Nested(StatsMilestones())
    hails_incident_taxi = fields.Nested(StatsMilestones())
    hails_incident_customer = fields.Nested(StatsMilestones())
    hails_timeout_accepted_by_customer = fields.Nested(StatsMilestones())
    hails_failure = fields.Nested(StatsMilestones())
    hails_total = fields.Nested(StatsHailsTotal())
    hails_average = fields.Nested(StatsHailsAverage())
    average_times = fields.Nested(StatsAverageTimes())
    average_hail_distance = fields.Nested(StatsMilestones())


class FleetDataSchema(Schema):
    id = fields.Integer()
    email = fields.String()
    fleet_size = fields.Integer()
    count = fields.Integer()
    ratio = fields.Float()
    last_taxi = fields.DateTime()
    manager = fields.String()


class StatsGroupementsSchema(Schema):
    registered_groupements = fields.Integer()
    fleet_data = fields.List(fields.Nested(FleetDataSchema))


class StatsADSmapSchema(Schema):
    count = fields.Integer()
    insee = fields.String()
    position = fields.Raw()
    name = fields.String()


class StationSchema(Schema):
    id = fields.String()
    name = fields.String()
    places = fields.Integer()
    geojson = fields.Raw()


class GroupSchema(Schema):
    id = fields.Integer()
    email = fields.String()
    commercial_name = fields.String()


class PublicStatsSchema(Schema):
    groups = fields.Integer()
    apps = fields.Integer()
    # Key is the month
    taxis_connected = fields.List(fields.Tuple([fields.Date(), fields.Dict(keys=fields.Str(), values=fields.Float())]))
    # Key is the conurbation ID
    hails_growth = fields.Dict(keys=fields.Str(), values=fields.Float())


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
DataSearchTaxiSchema = data_schema_wrapper(SearchTaxiSchema())
DataCreateHailSchema = data_schema_wrapper(CreateHailSchema())
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
DataStatsTaxisSchema = data_schema_wrapper(StatsTaxisSchema())
DataStatsHailsSchema = data_schema_wrapper(StatsHailsSchema())
DataStatsGroupementsSchema = data_schema_wrapper(StatsGroupementsSchema())
DataStatsADSmapSchema = data_schema_wrapper(StatsADSmapSchema())
DataStationSchema = data_schema_wrapper(StationSchema())
DataGroupSchema = data_schema_wrapper(GroupSchema())

# These schemas are only used to simplify the output of Swagger
DataCreateTaxiSchema = data_schema_wrapper(CreateTaxiSchema())
DataTaxiDetailsSchema = data_schema_wrapper(TaxiDetailsSchema())
