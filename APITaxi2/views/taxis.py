from datetime import datetime, timedelta
from functools import reduce

from flask import Blueprint, request
from flask_security import current_user, login_required, roles_accepted

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from APITaxi_models2 import (
    ADS,
    db,
    Departement,
    Driver,
    Taxi,
    Vehicle,
    VehicleDescription,
    ZUPC,
)

from .. import debug, redis_backend, schemas
from ..utils import get_short_uuid
from ..validators import (
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('taxis', __name__)


@blueprint.route('/taxis', methods=['POST'])
@login_required
@roles_accepted('admin', 'operateur')
def taxis_create():
    """Endpoint POST /taxis to create Taxi object. If the taxi already exists, which is
    defined as the combination of an ads, a vehicle and a driver, it is
    returned instead of being created.

    ---
    post:
      description: |
        Create a new taxi. Taxi is the combination of an ADS, a Vehicle and a
        Driver. If the resource already exists, the existing resource is
        returned.
      requestBody:
        content:
          application/json:
            schema: DataTaxiSchema
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: Return the existing ressource.
          content:
            application/json:
              schema: DataTaxiSchema
        201:
          description: Return a new ressource.
    """
    schema = schemas.DataTaxiSchema()

    params, errors = validate_schema(schema, request.json)
    if errors:
        return make_error_json_response(errors)

    args = params['data'][0]

    errors = {}

    ads = ADS.query.filter_by(
        insee=args['ads']['insee'],
        numero=args['ads']['numero'],
        added_by=current_user
    ).order_by(ADS.id.desc()).first()
    if not ads:
        errors['ads'] = {
            'insee': ['ADS not found with this INSEE/numero'],
            'numero': ['ADS not found with this INSEE/numero']
        }
    vehicle = Vehicle.query.options(joinedload('*')).filter_by(
        licence_plate=args['vehicle']['licence_plate']
    ).one_or_none()
    if not vehicle:
        errors['vehicle'] = {
            'licence_plate': ['Invalid licence plate']
        }
    else:
        for vehicle_description in vehicle.descriptions:
            if vehicle_description.added_by == current_user:
                break
        else:
            errors['vehicle'] = {
                'licence_plate': ['Vehicle exists but has not been created by the user making the request']
            }

    departement = Departement.query.filter_by(
        numero=args['driver']['departement']['numero']
    ).one_or_none()
    if not departement:
        errors['driver'] = {
            'departement': ['Departement not found']
        }

    driver = Driver.query.options(joinedload('*')).filter_by(
        professional_licence=args['driver']['professional_licence'],
        departement=departement,
        added_by=current_user
    ).order_by(Driver.id.desc()).first()
    if not driver:
        if 'driver' not in errors:
            errors['driver'] = {}
        errors['driver'].update({
            'professional_licence': ['Driver not found with this professional_licence. Is it the correct departement?'],
        })

    if errors:
        return make_error_json_response({
            'data': {'0': errors}
        }, status_code=404)

    # Try to get existing Taxi, or create it.
    taxi = Taxi.query.options(joinedload('*')).filter_by(
        ads=ads,
        driver=driver,
        vehicle=vehicle,
        added_by=current_user
    ).order_by(Taxi.id.desc()).first()

    status_code = 200

    if not taxi:
        status_code = 201
        taxi = Taxi(
            id=get_short_uuid(),
            vehicle=vehicle,
            ads=ads,
            added_by=current_user,
            driver=driver,
            added_via='api',
            added_at=func.NOW(),
            source='added_by',
        )
        db.session.add(taxi)
        db.session.flush()

    ret = schema.dump({'data': [(taxi, vehicle_description)]})

    db.session.commit()

    return ret, status_code


@blueprint.route('/taxis/<string:taxi_id>', methods=['GET', 'PUT'])
@login_required
@roles_accepted('admin', 'operateur')
def taxis_details(taxi_id):
    """Get or update a taxi.

    Taxi update is possible with PUT /taxis/:id. To keep backward
    compatibility, it is only possible to change the field `status`.
    ---
    get:
      description: Get taxi details.
      parameters:
        - name: taxi_id
          in: path
          required: true
          schema:
            type: string
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: Taxi details.
          content:
            application/json:
              schema: DataTaxiSchema

    put:
      description: Edit taxi status. Only the field `status` can be changed.
      parameters:
        - name: taxi_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema: TaxiPUTSchema
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: Edit taxi status.
          content:
            application/json:
              schema: DataTaxiSchema
    """
    # Get Taxi object with the VehicleDescription entry related to current
    # user.
    query = db.session.query(Taxi, VehicleDescription).options(
        joinedload(Taxi.ads),
        joinedload(Taxi.driver).joinedload(Driver.departement),
        joinedload(Taxi.vehicle).joinedload(Vehicle.descriptions).joinedload(VehicleDescription.added_by),
        joinedload(Taxi.added_by),
        joinedload(Taxi.current_hail)
    ).filter(
        VehicleDescription.vehicle_id == Taxi.vehicle_id
    ).filter(
        Taxi.id == taxi_id,
        VehicleDescription.added_by == current_user
    )

    res = query.one_or_none()
    if not res:
        return make_error_json_response({
            'url': ['Unknown taxi %s, or taxi exists but you are not the owner.' % taxi_id]
        }, status_code=404)
    taxi, vehicle_description = (res.Taxi, res.VehicleDescription)

    redis_taxi = redis_backend.get_taxi(taxi.id, vehicle_description.added_by.email)
    location = None
    if redis_taxi:
        location = redis_backend.Location(
            lon=redis_taxi.lon,
            lat=redis_taxi.lat,
            distance=None,
            update_date=datetime.fromtimestamp(redis_taxi.timestamp)
        )

    # Build Schema
    schema = schemas.DataTaxiSchema()

    # Dump data for GET requests
    if request.method != 'PUT':
        return schema.dump({'data': [(taxi, vehicle_description, location)]})

    params, errors = validate_schema(schema, request.json, partial=True)
    if errors:
        return make_error_json_response(errors)

    args = request.json['data'][0]

    # For now it is only possible to update the taxi's status. In the future,
    # We should allow the edition of other fields (taxi.internal_id, ...).
    if 'status' in args and args['status'] != vehicle_description.status:
        taxi.last_update_at = func.now()
        db.session.flush()

        vehicle_description.last_update_at = func.now()
        vehicle_description.status = args['status']
        db.session.flush()

        redis_backend.set_taxi_availability(
            taxi_id,
            vehicle_description.added_by.email,
            vehicle_description.status == 'free'
        )

        # Store history
        redis_backend.log_taxi_status(
            taxi_id,
            args['status']
        )

    output = schema.dump({'data': [(taxi, vehicle_description, location)]})

    db.session.commit()

    return output


@blueprint.route('/taxis', methods=['GET'])
@login_required
@roles_accepted('admin', 'moteur')
def taxis_list():
    """Get the taxis around a location.

    * Most of locations should belong to zero or one ZUPC, but some might
      belong to several, for example at borders.

    * geotaxi stores data into redis.
        To retrieve the longitude and latitude of taxis:
            - geoindex: HSET key = <taxi_id>
            - geoindex_2: HSET key = <taxi_id:operator_id>

        To retrieve last time the update request has been received:
            - timestamps: HSET key = <taxi_id:operator_id>
            - timestamps_id: HSET key = <taxi_id>

    * when a taxi turns off with PUT /taxis { status: off }, the entry
    "<taxi_id:operator_id>" is appended to the set not_available.
    ---
    get:
      description: List available taxis around a location.
      parameters:
        - name: lon
          schema:
            type: string
          required: true
          in: query
        - name: lat
          required: true
          schema:
            type: string
          in: query
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: List available taxis around a location.
          content:
            application/json:
              schema: DataTaxiSchema
    """
    debug_ctx = debug.DebugContext()

    schema = schemas.ListTaxisQueryStringSchema()
    params, errors = validate_schema(schema, request.args)
    if errors:
        return make_error_json_response(errors)

    zupcs = ZUPC.query.filter(
        func.ST_Intersects(ZUPC.shape, 'Point({} {})'.format(params['lon'], params['lat'])),
    ).all()
    debug_ctx.log(f'List of zupcs matching lon={params["lon"]} lat={params["lat"]}', [{
        'id': zupc.id,
        'nom': zupc.nom
    } for zupc in zupcs])

    schema = schemas.DataTaxiSchema()

    if not zupcs:
        debug_ctx.log('No ZUPC maching')
        return schema.dump({'data': []})

    # This variable used to be in configuration file, but I don't think it
    # makes much sense to have it configurable globally. Configuration should
    # ideally be fine grained, depending on day, time, location, and be even
    # configurable by the taxi.
    default_max_distance = 500

    # Locations is a dict containing taxis close from the location given as
    # param. Each taxi can report its location from several operators.
    #
    # locations = {
    #    <taxi_id>: {
    #       <operator_id>: <location>,
    #       <operator_id>: <location>,
    #    }, ...
    # }
    #
    locations = redis_backend.taxis_locations_by_operator(
        params['lon'], params['lat'], default_max_distance
    )
    debug_ctx.log_admin(
        f'List of taxis around lon={params["lon"]} lat={params["lat"]}',
        locations
    )

    # Fetch all Taxi and VehicleDescriptions objects related to "locations".
    query = db.session.query(Taxi, VehicleDescription).join(
        ADS
    ).options(
        joinedload(Taxi.ads),
        joinedload(Taxi.driver).joinedload(Driver.departement),
        joinedload(Taxi.vehicle).joinedload(Vehicle.descriptions).joinedload(VehicleDescription.added_by),
        joinedload(Taxi.added_by),
        joinedload(Taxi.current_hail)
    ).filter(
        VehicleDescription.vehicle_id == Taxi.vehicle_id
    ).filter(
        Taxi.id.in_(locations.keys()),
        # Removes taxis with an ADS located in another ZUPC than the one where
        # the request is made. For example, if a taxi from Bordeaux reports
        # it's location in Paris, we don't want it returned for a request in
        # Paris.
        ADS.zupc_id.in_([zupc.id for zupc in zupcs])
    )

    # Create data as a dictionary such as:
    #
    # {
    #   <taxi>: {
    #     <vehicle_description>: <location>
    #     ...
    #   }
    # }
    #
    # VehicleDescription holds the link between the taxi object and an operator.
    data = {}
    for taxi, vehicle_description in query.all():
        if taxi not in data:
            data[taxi] = {}

        # If a taxi has two VehicleDescription but only reports it's location
        # with one operator, the query above will return 2 rows.
        # Skip the VehicleDescription if we don't have location for it.
        if vehicle_description.added_by.email not in locations[taxi.id]:
            continue

        data[taxi][vehicle_description] = locations[taxi.id][vehicle_description.added_by.email]

    # Taxis can report their locations with several operators. If
    # favorite_operator is set:
    # - if the taxi reports its location with this operator, discard all other
    #   entries
    # - otherwise, keep all entries
    if params.get('favorite_operator'):
        for taxi in data:
            filtered = next((
                vehicle_description for vehicle_description in data[taxi]
                if vehicle_description.added_by.email == params['favorite_operator']
            ), None)
            if filtered:
                data[taxi] = {
                    filtered: data[taxi][filtered]
                }

    # For each location reported, only keep if the location has been reported
    # less than 120 seconds ago, and if the taxi is available.
    now = datetime.now()
    data = {
        taxi: {
            description: location
            for description, location in data[taxi].items()
            if description.status == 'free'
            and location.update_date
            and location.update_date + timedelta(seconds=120) >= now
        }
        for taxi in data
    }

    # Remove empty entries, ie. taxis off or with an old update date.
    data = {
        taxi: data[taxi]
        for taxi in data
        if data[taxi]
    }

    # For each taxi taxi, only keep the VehicleDescription with the latest
    # update date.
    # If a taxi reports its location from 2 different operators, we will always
    # return the data from the same operator.
    data = {
        taxi: reduce(
            lambda a, b:
                a if a[0].last_update_at
                and b[0].last_update_at
                and a[0].last_update_at >= b[0].last_update_at
                else b,
                data[taxi].items()
        )
        for taxi in data
    }

    # schema.dump expects a list of tuples
    # (taxi, vehicle_description, location).
    data = [
        (taxi, vehicle_description, redis_location)
        for taxi, (vehicle_description, redis_location) in data.items()
    ]

    # Sort entries by distance.
    data = sorted(
        data,
        key=lambda o: o[2].distance
    )

    # Only keep "count" entries.
    if 'count' in params:
        data = data[:params['count']]

    return debug_ctx.add_to_response(schema.dump({'data': data}))
