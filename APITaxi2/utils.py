from flask import current_app
import requests
import shortuuid


REVERSE_API_URL = 'https://api-adresse.data.gouv.fr/reverse/'


def get_short_uuid():
    suid = shortuuid.ShortUUID()
    return suid.uuid()[:7]


def reverse_geocode(lon, lat):
    try:
        response = requests.get(REVERSE_API_URL, {'lon': lon, 'lat': lat, 'limit': 1})
        properties = response.json()['features'][0]['properties']
        return "{name}, {city}".format(**properties)
    except (KeyError, requests.RequestException) as exc:
        current_app.logger.warning('Exception in reverse geocoding', exc_info=True)
        # Play it safe, ignore network errors, etc.
        return ""
