from flask_influxdb import InfluxDB as _InfluxDB
from flask import current_app, Flask

from datetime import datetime
import hashlib

class InfluxDB(_InfluxDB):
    def init_app(self, app: Flask) -> None:
        with app.app_context():
            if current_app.config.get('INFLUXDB_TAXIS_DB'):
                current_app.config.setdefault(
                    'INFLUXDB_DATABASE',
                    current_app.config['INFLUXDB_TAXIS_DB']
                )
        try:
            super().init_app(app=app)
        except Exception as e:
            app.logger.error('Unable to init influxdb connection {}'.format(e))
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['influx_db'] = self

    def write_point(self, db, measurement, tags, value=1):
        try:
            self.write_points([{
                "measurement": measurement,
                "tags": tags,
                "time": datetime.utcnow().strftime('%Y%m%dT%H:%M:%SZ'),
                "fields": {
                    "value": value
                }
                }])
        except Exception as e:
            current_app.logger.error('Influxdb Error: {}'.format(e))


    def write_get_taxis(self, zupc_insee, lon, lat, moteur, request, l_taxis):
            self.write_point(
                current_app.config['INFLUXDB_TAXIS_DB'],
                "get_taxis_requests",
                {
                    "zupc": zupc_insee,
                    "position": "{:.3f}:{:.3f}".format(float(lon), float(lat)),
                    "moteur": moteur,
                    "customer": hashlib.sha224(str(
                        (
                            request.headers.getlist("X-Forwarded-For")[0].rpartition(' ')[-1]
                            if 'X-Forwarded-For' in request.headers
                            else request.remote_addr
                                            ) or 'untrackable'
                                            ).encode('utf-8')
                                    ).hexdigest()[:10]
                },
                value=l_taxis
            )
