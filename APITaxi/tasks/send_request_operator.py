#coding: utf-8
from flask import current_app
from flask_restplus import marshal
from APITaxi_models.hail import Hail, HailLog, db
from ..descriptors.hail import hail_model
from ..extensions import celery, redis_store_saved
import requests, json


@celery.task()
def send_request_operator(hail_id, endpoint, operator_header_name,
        operator_api_key, operator_email):
    operator_api_key = operator_api_key.encode('utf-8')
    operator_header_name = operator_header_name.encode('utf-8')
    hail = Hail.query.get(hail_id)
    if not hail:
        current_app.logger.error('Unable to find hail: {}'.format(hail_id))
        return False

    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}
    if operator_header_name is not None and operator_header_name != '':
        headers[operator_header_name] = operator_api_key

    data = None
    try:
        data = json.dumps(marshal({"data": [hail]}, hail_model))
    except ValueError:
        current_app.logger.error('Unable to dump JSON ({})'.format(hail))

    if data:
        r = None
        hail_log = HailLog('POST to operator', hail, data)
        try:
            r = requests.post(endpoint,
                    data=data,
                    headers=headers
            )
        except requests.exceptions.RequestException as e:
            current_app.logger.error('Error calling: {}, endpoint: {}, headers: {}'.format(
                operator_email, endpoint, headers))
            current_app.logger.error(e)
            hail_log.store(None, redis_store_saved, str(e))
    if r:
        hail_log.store(r, redis_store_saved)
    if not r or r.status_code < 200 or r.status_code >= 300:
        hail.status = 'failure'
        db.session.commit()
        current_app.logger.error("Unable to reach hail's endpoint {} of operator {}"\
            .format(endpoint, operator_email))
        return False
    r_json = None
    try:
        r_json = r.json()
    except ValueError:
        current_app.logger.error("unable to get json")
        pass

    if r_json and 'data' in r_json and len(r_json['data']) == 1\
            and 'taxi_phone_number' in r_json['data'][0]:
        hail.taxi_phone_number = str(r_json['data'][0]['taxi_phone_number'])
    else:
        current_app.logger.error('No JSON in operator answer of {} : {}'.format(
            operator_email, r.text))

    hail.status = 'received_by_operator'
    db.session.add(hail)
    db.session.commit()

    h = Hail.query.get(hail.id)
    return True
