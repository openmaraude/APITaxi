# -*- coding: utf-8 -*-
from flask import request, current_app, g
from flask_restplus import Resource, reqparse, fields, abort, marshal
from flask_security import (login_required, roles_required,
        roles_accepted, current_user)
from flask_restplus import reqparse
from ..extensions import redis_store, redis_store_saved
from ..api import api
from APITaxi_models.hail import Hail as HailModel, Customer as CustomerModel, HailLog
from APITaxi_models.taxis import  RawTaxi, TaxiRedis, Taxi
from APITaxi_models import security as security_models
from ..descriptors.hail import (hail_model, hail_expect_post, hail_expect_put,
        puttable_arguments)
from APITaxi_utils.request_wants_json import json_mimetype_required
from geopy.distance import vincenty
from ..tasks import send_request_operator
from APITaxi_utils import influx_db
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
        if not current_user.id in (hail.operateur_id, hail.added_by) and\
                not current_user.has_role('admin'):
            abort(403, message="You don't have the authorization to view this hail")


    @login_required
    @roles_accepted('admin', 'moteur', 'operateur')
    @json_mimetype_required
    def get(self, hail_id):
        from APITaxi_models import db
        db.session.expire_all()
        hail = HailModel.get_or_404(hail_id)
        self.filter_access(hail)
        hail.taxi_relation = Taxi.query.from_statement(
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
        hail = HailModel.get_or_404(hail_id)
        g.hail_log = HailLog('PUT', hail, request.data)
        self.filter_access(hail)
        if hail.status.startswith("timeout"):
            return {"data": [hail]}
        hj = request.json
        hj = hj['data'][0]

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
            except AssertionError, e:
                if e.args:
                    abort(400, message=e.args[0])
                else:
                    abort(400,
                        message="Unable to set {} to {}, validation failed".format(ev, value))
            except RuntimeError, e:
                abort(403)
            except ValueError, e:
                abort(400, message=e.args[0])
        current_app.extensions['sqlalchemy'].db.session.add(hail)
        current_app.extensions['sqlalchemy'].db.session.commit()
        return {"data": [hail]}


@ns_hail.route('/', endpoint='hail_endpoint')
class Hail(Resource):

    @login_required
    @roles_accepted('admin', 'moteur')
    @api.expect(hail_expect_post, validate=True)
    @api.response(201, 'Success', hail_model)
    @json_mimetype_required
    def post(self):
        hj = request.json
        hj = hj['data'][0]

        operateur = security_models.User.filter_by_or_404(
                email=hj['operateur'],
                message='Unable to find the taxi\'s operateur')

        descriptions = RawTaxi.get((hj['taxi_id'],), operateur.id)
        if len(descriptions) == 0 or len(descriptions[0]) == 0:
            g.hail_log = HailLog('POST', None, request.data)
            abort(404, message='Unable to find taxi {} of {}'.format(
                hj['taxi_id'], hj['operateur']))
        if descriptions[0][0]['vehicle_description_status'] != 'free' or\
                not TaxiRedis(hj['taxi_id']).is_fresh(hj['operateur']):
            g.hail_log = HailLog('POST', None, request.data)
            abort(403, message="The taxi is not available")
        customer = CustomerModel.query.filter_by(id=hj['customer_id'],
                moteur_id=current_user.id).first()
        if not customer:
            customer = CustomerModel(hj['customer_id'])
            current_app.extensions['sqlalchemy'].db.session.add(customer)
        taxi_pos = redis_store.geopos(current_app.config['REDIS_GEOINDEX'],
                '{}:{}'.format(hj['taxi_id'], operateur.email))

        hail = HailModel()
        hail.customer_id = hj['customer_id']
        hail.customer_lon = hj['customer_lon']
        hail.customer_lat = hj['customer_lat']
        hail.customer_address = hj['customer_address']
        hail.customer_phone_number = hj['customer_phone_number']
        hail.taxi_id = hj['taxi_id']
        hail.initial_taxi_lat = taxi_pos[0][0] if taxi_pos else None
        hail.initial_taxi_lon = taxi_pos[0][1] if taxi_pos else None
        hail.operateur_id = operateur.id
        if customer.ban_end and datetime.now() < customer.ban_end:
            hail.status = 'customer_banned'
            current_app.extensions['sqlalchemy'].db.session.add(hail)
            current_app.extensions['sqlalchemy'].db.session.commit()
            abort(403, message='Customer is banned')
        hail.status = 'received'
        current_app.extensions['sqlalchemy'].db.session.add(hail)
        current_app.extensions['sqlalchemy'].db.session.commit()

        taxi = Taxi.query.get(hail.taxi_id)
        taxi.current_hail_id = hail.id

        g.hail_log = HailLog('POST', hail, request.data)
        current_app.extensions['sqlalchemy'].db.session.add(hail)
        current_app.extensions['sqlalchemy'].db.session.commit()

        send_request_operator.apply_async(args=[hail.id,
            operateur.hail_endpoint(current_app.config['ENV']),
            unicode(operateur.operator_header_name),
            unicode(operateur.operator_api_key), operateur.email],
            queue='send_hail_'+current_app.config['NOW'])

        client = influx_db.get_client(current_app.config['INFLUXDB_TAXIS_DB'])
        if client:
            try:
                client.write_points([{
                    "measurement": "hails_created",
                    "tags": {
                        "added_by": current_user.email,
                        "operator": operateur.email,
                        "zupc": descriptions[0][0]['ads_insee'],
                        "geohash": Geohash.encode(hail.customer_lat, hail.customer_lon),
                        },
                    "time": datetime.utcnow().strftime('%Y%m%dT%H:%M:%SZ'),
                    "fields": {
                        "value": 1
                    }
                    }])
            except Exception as e:
                current_app.logger.error('Influxdb Error: {}'.format(e))
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
        q = HailModel.query
        filters = []
        if not current_user.has_role('admin'):
            if current_user.has_role('operateur'):
                filters.append(HailModel.operateur_id == current_user.id)
            if current_user.has_role('moteur'):
                filters.append(HailModel.added_by == current_user.id)
            if filters:
                q = q.filter(or_(*filters))
        else:
            uq = security_models.User.query
            if p['operateur']:
                q = q.filter(or_(*[
                    HailModel.operateur_id == uq.filter_by(email=email).first().id
                     for email in p['operateur']]
                ))
            if p['moteur']:
                q = q.filter(or_(*[
                    HailModel.added_by == uq.filter_by(email=email).first().id
                     for email in p['moteur']]
                ))
        if p['status']:
            q = q.filter(or_(*[HailModel._status == s for s in p['status']]))
        if p['date']:
            date = None
            try:
                date = datetime.strptime(p['date'], '%Y/%m/%d')
            except ValueError:
                current_app.logger.info('Unable to parse date: {}'.format(p['date']))
            if date:
                q = q.filter(HailModel.creation_datetime <= date)
        if p['taxi_id']:
            q = q.filter(HailModel.taxi_id == p['taxi_id'])

        q = q.order_by(HailModel.creation_datetime.desc())
        pagination = q.paginate(page=p['p'], per_page=30)
        return {"data": [{
                "id": hail.id,
                "added_by": security_models.User.query.get(hail.added_by).email,
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


@ns_hail.route('/<string:hail_id>/_log', endpoint='HailLog')
class Hail(Resource):
    @login_required
    def get(self, hail_id):
        hail = HailModel.query.get_or_404(hail_id)
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
