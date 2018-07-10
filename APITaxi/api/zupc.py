# -*- coding: utf-8 -*-
from . import api, ns_administrative
from APITaxi_utils.resource_metadata import ResourceMetadata
from APITaxi_utils.request_wants_json import request_wants_json
from APITaxi_utils.caching import cache_single
from APITaxi_utils import influx_db
from flask_restplus import reqparse, abort, marshal
from flask import current_app
from werkzeug.exceptions import BadRequest
import json
from psycopg2.extras import RealDictCursor
import APITaxi_models as models
from influxdb.exceptions import InfluxDBClientError


@ns_administrative.route('zupc/')
class ZUPC(ResourceMetadata):
    def get(self):
        if not request_wants_json():
            abort(400, message="request needs JSON")
        parser = reqparse.RequestParser()
        parser.add_argument('lon', type=float, required=True, location='args')
        parser.add_argument('lat', type=float, required=True, location='args')
        try:
            args = parser.parse_args()
        except BadRequest as e:
            return json.dumps(e.data), 400, {"Content-Type": "application/json"}

        zupc_list = cache_single(
            """SELECT insee, active, nom
               FROM "ZUPC"
               WHERE ST_INTERSECTS(shape, 'POINT(%s %s)')
               AND parent_id = id
               ORDER BY max_distance ASC;""",
            (args.get('lon'), args.get('lat')), "zupc_list",
            lambda v: (v['id'], v['parent_id']),
            get_id=lambda a:(float(a[1].split(",")[0][1:].strip()),
                             float(a[1].split(",")[1][:-1].strip()))
        )
        to_return = []
        client = influx_db.get_client(current_app.config['INFLUXDB_TAXIS_DB'])
        for zupc in zupc_list:
            if any(map(lambda z: zupc[0] == z['insee'], to_return)):
                current_app.logger.debug("ZUPC {} already added, skipping it".format(zupc[0]))
                continue
            to_return.append({"insee": zupc[0], "active": zupc[1], "nom": zupc[2]})
            if not client:
                current_app.logger.error("No influxdb client")
                continue
            request = """SELECT "value" FROM "nb_taxis_every_1" WHERE "zupc" = '{}' AND "operator" = ''  AND time > now() - 1m  fill(null) LIMIT 1;""".format(zupc['insee'])
            try:
                r = client.query(request)
            except InfluxDBClientError, e:
                current_app.logger.error(e)
                continue
            points = list(r.get_points())
            if len(points) <= 0:
                current_app.logger.debug("No stat points found, request: \"{}\"".format(request))
                continue
            to_return[-1]['nb_active'] = points[0].get('value')
        return {"data": to_return}, 200


@ns_administrative.route('/zupc/autocomplete')
@api.hide
class ZUPCAutocomplete(ResourceMetadata):
    def get(self):
        #@TODO: have some identification here?
        term = request.args.get('q')
        like = "%{}%".format(term)

        response = models.ZUPC.query.filter(
                models.ZUPC.nom.ilike(like)).all()
        return jsonify(suggestions=map(lambda zupc:{'name': zupc.nom, 'id': int(zupc.id)},
                                            response))

@ns_administrative.route('zupc/<int:zupc_id>/_show_temp_geojson')
@api.hide
class ZUPCShowTemp(ResourceMetadata):
    def get(self, zupc_id):
        cur = current_app.extensions['sqlalchemy'].db.session.connection()\
                .connection.cursor()
        cur.execute('SELECT ST_AsGeoJSON(shape) FROM "zupc_temp" WHERE id = %s;',
                (zupc_id,)
        )
        geojson = cur.fetchall()
        if not geojson:
            return {"data": None}
        else:
            return {"data": json.loads(geojson[0][0])}

