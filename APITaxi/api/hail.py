# -*- coding: utf-8 -*-
from flask import request, current_app, g
from flask_restplus import Resource, reqparse, fields, abort, marshal
from flask_security import (login_required, roles_required,
        roles_accepted, current_user)
from ..extensions import redis_store, redis_store_saved
from ..api import api
import APITaxi_models as models
from ..descriptors.hail import (hail_model, hail_expect_post, hail_expect_put,
        puttable_arguments)
from APITaxi_utils.request_wants_json import json_mimetype_required
from geopy.distance import vincenty
from ..tasks import send_request_operator
from APITaxi_utils import influx_db, reqparse
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json, Geohash
from sqlalchemy import or_
from itertools import chain
from sqlalchemy.sql.expression import text


ns_hail = api.namespace('hails', description="Hail API")
@ns_hail.route('/<string:hail_id>/', endpoint='hailid')
class HailId(Resource):

    @classmethod
    def filter_access(cls, hail):
        if current_user.id not in (hail.operateur_id, hail.added_by) and\
                not current_user.has_role('admin'):
            abort(403, message="You don't have the authorization to view this hail")


    @login_required
    @roles_accepted('admin', 'moteur', 'operateur')
    @json_mimetype_required
    def get(self, hail_id):
        models.db.session.expire_all()
        hail = models.Hail.get_or_404(hail_id)
        self.filter_access(hail)
        hail.taxi_relation = models.Taxi.query.from_statement(
            text("SELECT * FROM taxi where id=:taxi_id")
        ).params(taxi_id=hail.taxi_id).one()
        return_ = marshal({"data": [hail]},hail_model)
        if hail._status in ('finished', 'customer_on_board',
            'timeout_accepted_by_customer'):
            return_['data'][0]['taxi']['position']['lon'] = 0.0
            return_['data'][0]['taxi']['position']['lat'] = 0.0
            return_['data'][0]['taxi']['last_update'] = 0
        else:
            return_['data'][0]['taxi']['crowfly_distance'] = vincenty(
                (return_['data'][0]['taxi']['position']['lat'],
                return_['data'][0]['taxi']['position']['lon']),
                (return_['data'][0]['customer_lat'],
                 return_['data'][0]['customer_lon'])
                ).kilometers
        return return_

    @login_required
    @roles_accepted('admin', 'moteur', 'operateur')
    @api.marshal_with(hail_model)
    @api.expect(hail_expect_put, validate=True)
    @json_mimetype_required
    def put(self, hail_id):
        hail = models.Hail.get_or_404(hail_id)
        g.hail_log = models.HailLog('PUT', hail, request.data)
        self.filter_access(hail)
        if hail.status.startswith("timeout"):
            return {"data": [hail]}
        parser = reqparse.DataJSONParser()
        hj = parser.get_data()[0]

        #We change the status
        if 'status' in hj and  hj['status'] == 'accepted_by_taxi':
            if g.version == 2:
                if not 'taxi_phone_number' in hj or hj['taxi_phone_number'] == '':
                    abort(400, message='Taxi phone number is needed')
                else:
                    hail.taxi_phone_number = hj['taxi_phone_number']
        initial_rating = hail.rating_ride
        for ev in puttable_arguments:
            if current_user.id != hail.added_by and ev.startswith('customer'):
                continue
            value = hj.get(ev, None)
            if value is None:
                continue
            try:
                setattr(hail, ev, value)
            except RuntimeError, e:
                abort(403)
            except ValueError, e:
                abort(400, message=e.args[0])
        models.db.session.add(hail)
        models.db.session.commit()
        return {"data": [hail]}


@ns_hail.route('/', endpoint='hail_endpoint')
class Hail(Resource):

    @login_required
    @roles_accepted('admin', 'moteur')
    @api.expect(hail_expect_post, validate=True)
    @api.response(201, 'Success', hail_model)
    @json_mimetype_required
    def post(self):
        parser = reqparse.DataJSONParser(filter_=hail_expect_post)
        hj = parser.get_data()[0]
        hj['status'] = 'received'
        hail = models.Hail(**hj)
        models.db.session.add(hail)
        models.db.session.commit()

        g.hail_log = models.HailLog('POST', hail, request.data)
        send_request_operator.apply_async(args=[hail.id,
            hail.operateur.hail_endpoint(current_app.config['ENV']),
            unicode(hail.operateur.operator_header_name),
            unicode(hail.operateur.operator_api_key), hail.operateur.email],
            queue='send_hail_'+current_app.config['NOW'])

        influx_db.write_point(current_app.config['INFLUXDB_TAXIS_DB'],
                             "hails_created",
                             {
                                 "added_by": current_user.email,
                                 "operator": hail.operateur.email,
                                 "zupc": hail.ads_insee,
                                 "geohash": Geohash.encode(hail.customer_lat, hail.customer_lon),
                             }
        )
        result = marshal({"data": [hail]}, hail_model)
        result['data'][0]['taxi']['lon'] = hail.initial_taxi_lon
        result['data'][0]['taxi']['lat'] = hail.initial_taxi_lat
        return result, 201

    @login_required
    @roles_accepted('admin', 'moteur', 'operateur')
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('p', type=int, required=False, default=None,
                location='values')
        parser.add_argument('operateur', type=str, required=False, default=None,
                            location='values', action='append')
        parser.add_argument('status', type=str, required=False, default=None,
                            location='values', action='append')
        parser.add_argument('moteur', type=str, required=False, default=None,
                            location='values', action='append')
        parser.add_argument('date', type=str, required=False, default=None,
                            location='values')
        parser.add_argument('taxi_id', type=str, required=False, default=None,
                            location='values')
        p = parser.parse_args()
        q = models.Hail.query
        filters = []
        if not current_user.has_role('admin'):
            if current_user.has_role('operateur'):
                filters.append(models.Hail.operateur_id == current_user.id)
            if current_user.has_role('moteur'):
                filters.append(models.Hail.added_by == current_user.id)
            if filters:
                q = q.filter(or_(*filters))
        else:
            uq = models.security.User.query
            if p['operateur']:
                q = q.filter(or_(*[
                    models.Hail.operateur_id == uq.filter_by(email=email).first().id
                     for email in p['operateur']]
                ))
            if p['moteur']:
                q = q.filter(or_(*[
                    models.Hail.added_by == uq.filter_by(email=email).first().id
                     for email in p['moteur']]
                ))
        if p['status']:
            q = q.filter(or_(*[models.Hail._status == s for s in p['status']]))
        if p['date']:
            date = None
            try:
                date = datetime.strptime(p['date'], '%Y/%m/%d')
            except ValueError:
                current_app.logger.info('Unable to parse date: {}'.format(p['date']))
            if date:
                q = q.filter(models.Hail.creation_datetime <= date)
        if p['taxi_id']:
            q = q.filter(models.Hail.taxi_id == p['taxi_id'])

        q = q.order_by(models.Hail.creation_datetime.desc())
        pagination = q.paginate(page=p['p'], per_page=30)
        return {"data": [{
                "id": hail.id,
                "added_by": models.security.User.query.get(hail.added_by).email,
                "operateur": hail.operateur.email,
                "status": hail.status,
                "creation_datetime": hail.creation_datetime.strftime("%Y/%m/%d %H:%M:%S"),
                "taxi_id": hail.taxi_id}
                for hail in pagination.items
            ],
            "meta": {
                "next_page": pagination.next_num if pagination.has_next else None,
                "prev_page": pagination.prev_num if pagination.has_prev else None,
                "pages": pagination.pages,
                "iter_pages": list(pagination.iter_pages()),
                "total": pagination.total
                }
            }


@ns_hail.route('/<string:hail_id>/_log', endpoint='models.HailLog')
class Hail(Resource):
    @login_required
    def get(self, hail_id):
        hail = models.Hail.query.get_or_404(hail_id)
        if current_user.id not in (hail.added_by, hail.operateur_id)\
                and not current_user.has_role('admin'):
            abort(403)
        hlog = redis_store_saved.zrangebyscore('hail:{}'.format(hail_id), '-inf',
                '+inf', withscores=True)
        if not hlog:
            return {"data": []}
        return {"data":[
            {k: v for k,v in chain(json.loads(value).iteritems(), [('datetime', score)])}
            for value, score in hlog
            ]
        }
