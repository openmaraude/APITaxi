import datetime
import functools

from flask import Blueprint, current_app, request
from geoalchemy2 import Geometry
from marshmallow import fields, Schema, validate
from shapely import wkt
from sqlalchemy import func, Text, or_
from sqlalchemy.orm import aliased, joinedload
from sqlalchemy.dialects.postgresql import JSONB, INTERVAL

from APITaxi2 import auth
from APITaxi2 import redis_backend
from APITaxi2 import schemas
from APITaxi2.validators import make_error_json_response, validate_schema

from APITaxi_models2 import db, ADS, Driver, Taxi, VehicleDescription, Hail, Town, User
from APITaxi_models2 import Customer
from APITaxi_models2.zupc import town_zupc
from APITaxi_models2.stats import *


blueprint = Blueprint('internal_customers', __name__)


class ListCustomerSupportQuerystringSchema(Schema, schemas.PageQueryStringMixin):
    """Querystring arguments for GET /hails/."""
    id = fields.List(fields.String)
    moteur = fields.List(fields.String)
    operateur = fields.List(fields.String)
    status = fields.List(fields.String(
        validate=validate.OneOf(Hail.status.property.columns[0].type.enums),
    ))


class CustomerSupportListSchema(Schema):
    """Response schema for GET /hails/"""
    added_at = fields.DateTime()
    id = fields.String()
    moteur = fields.String()
    customer_lon = fields.Float()
    customer_lat = fields.Float()
    customer_phone_number = fields.String()
    operateur = fields.String()
    status = fields.String()
    taxi_phone_number = fields.String()


DataCustomerSupportListSchema = schemas.data_schema_wrapper(CustomerSupportListSchema(), with_pagination=True)


@blueprint.route('/internal/customers', methods=['GET'])
@auth.login_required(role=['admin'])
def customers():
    querystring_schema = ListCustomerSupportQuerystringSchema()
    querystring, errors = validate_schema(querystring_schema, dict(request.args.lists()))
    if errors:
        return make_error_json_response(errors)

    Operateur = aliased(User)
    Moteur = aliased(User)

    query = db.session.query(
        Hail.added_at,
        Hail.id,
        Moteur.email.label('moteur'),
        Hail.customer_lon,
        Hail.customer_lat,
        Hail.customer_phone_number,
        Operateur.email.label('operateur'),
        Hail.taxi_phone_number,
        Hail.status,
    ).join(
        Moteur, Hail.added_by_id == Moteur.id
    ).join(
        Operateur, Hail.operateur_id == Operateur.id
    ).filter(
        Hail.added_at < func.now() - func.cast('12 hours', INTERVAL()),
    ).order_by(
        Hail.added_at.desc()
    )

    # Filter on querystring arguments, partial match.
    for qname, field in (
        ('id', Hail.id),
        ('moteur', Moteur.email),
        ('operateur', Operateur.email),
    ):
        if qname not in querystring:
            continue
        query = query.filter(or_(*[
            func.lower(field).startswith(value.lower()) for value in querystring[qname]
        ]))

    # Filter on querystring arguments, exact match.
    for qname, field in (
        ('status', Hail.status),
    ):
        if qname not in querystring:
            continue
        query = query.filter(or_(*[
            field == value for value in querystring[qname]
        ]))

    hails = query.paginate(
        page=querystring.get('p', [1])[0],
        per_page=30,
        error_out=False  # if True, invalid page or pages without results raise 404
    )

    schema = DataCustomerSupportListSchema()
    ret = schema.dump({
        'data': hails.items,
        'meta': hails
    })

    return ret
