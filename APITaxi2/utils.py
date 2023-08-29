from flask import current_app
import requests
import shortuuid


REVERSE_API_URL = 'https://api-adresse.data.gouv.fr/reverse/'


def get_short_uuid():
    suid = shortuuid.ShortUUID()
    return suid.uuid()[:7]


def reverse_geocode(lon, lat):
    response = requests.get(REVERSE_API_URL, {'lon': lon, 'lat': lat, 'limit': 1})
    try:
        properties = response.json()['features'][0]['properties']
        return "{name}, {city}".format(**properties)
    except Exception:
        # Covers both local development and development environment
        if current_app.config.get('INTEGRATION_ENABLED'):
            raise
        # Play it safe, ignore network errors, etc.
        return ""
