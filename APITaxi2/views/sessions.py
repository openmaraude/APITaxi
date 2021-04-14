from flask import Blueprint, request
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import aliased

from flask_security import current_user, login_required, roles_accepted

from APITaxi_models2 import db, Hail, User

from .. import schemas
from ..validators import (
    make_error_json_response,
    validate_schema
)


blueprint = Blueprint('sessions', __name__)


@blueprint.route('/sessions')
@login_required
@roles_accepted('admin', 'moteur')
def hails_sessions():
    querystring_schema = schemas.ListHailsBySessionQuerystringSchema()
    querystring, errors = validate_schema(querystring_schema, dict(request.args.lists()))
    if errors:
        return make_error_json_response(errors)

    operateur = aliased(User)
    moteur = aliased(User)

    # SELECT customer_id, added_by_id, session_id, AGGREGATE_ORDER_BY(JSON_AGG(hail), added_at)
    # FROM hail ... GROUP BY customer_id, added_by_id, session_id
    #
    # returns one row for each hail for a customer/session_id/search provider.
    # AGGREGATE_ORDER_BY(JSON_AGG(...)) is a list of hails contained in the
    # GROUP BY.
    query = db.session.query(
        Hail.customer_id,
        Hail.added_by_id,
        Hail.session_id,
        func.MIN(Hail.added_at).label('added_at'),
        func.JSON_AGG(
            aggregate_order_by(
                func.JSON_BUILD_OBJECT(
                    'id', Hail.id,
                    'status', Hail.status,
                    'customer_lon', Hail.customer_lon,
                    'customer_lat', Hail.customer_lat,
                    'customer_address', Hail.customer_address,
                    'added_at', Hail.added_at,
                    'customer_phone_number', Hail.customer_phone_number,
                    'taxi_phone_number', Hail.taxi_phone_number,
                    'initial_taxi_lat', Hail.initial_taxi_lat,
                    'initial_taxi_lon', Hail.initial_taxi_lon,
                    'moteur', func.JSON_BUILD_OBJECT(
                        'id', moteur.id,
                        'email', moteur.email,
                        'commercial_name', moteur.commercial_name,
                    ),
                    'operateur', func.JSON_BUILD_OBJECT(
                        'id', operateur.id,
                        'email', operateur.email,
                        'commercial_name', operateur.commercial_name,
                    ),
                    'taxi', func.JSON_BUILD_OBJECT(
                        'id', Hail.taxi_id,
                    ),
                ),
                Hail.added_at
            )
        ).label('hails')
    ).join(
        operateur,
        Hail.operateur_id == operateur.id
    ).join(
        moteur,
        Hail.added_by_id == moteur.id
    ).group_by(
        Hail.customer_id,
        Hail.session_id,
        Hail.added_by_id
    ).order_by(
        func.MIN(Hail.added_at).desc()
    )

    if not current_user.has_role('admin'):
        query = query.filter(Hail.added_by == current_user)

    hails = query.paginate(
        page=querystring.get('p', [1])[0],
        per_page=30,
        error_out=False  # if True, invalid page or pages without results raise 404
    )

    schema = schemas.DataHailBySessionListSchema()
    ret = schema.dump({
        'data': hails.items,
        'meta': hails
    })

    return ret
