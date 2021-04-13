from celery import Celery

celery = Celery(__name__)

from .clean import clean_geoindex_timestamps  # noqa
from .operators import handle_hail_timeout, send_request_operator  # noqa
from .stats import store_active_taxis  # noqa
from .stations import compute_waiting_taxis_stations  # noqa
