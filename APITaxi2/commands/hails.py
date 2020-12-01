import datetime
import uuid

from flask import Blueprint, current_app
from sqlalchemy import func

from APITaxi_models2 import db, Hail


blueprint = Blueprint('commands_hails', __name__, cli_group=None)


@blueprint.cli.command('compute_session_ids')
def compute_session_ids():
    """Iterate on hails in chronological order to assign them a session ID where missing.

    Subsequent hails are considered to be the same user session when they happen close enough.

    This script should be interruptible at any time, and be resumed.
    """
    sessions = {}

    # Also include hails already assigned a session ID to rebuild the history
    for i, hail in enumerate(db.session.query(Hail).order_by(Hail.last_status_change)):
        # Customer IDs are unique to the search engine were they are registered
        key = (hail.customer_id, hail.added_by_id)

        # If this hail was already assigned a session ID, just record it
        if hail.session_id:
            sessions[key] = (hail.session_id, hail.last_status_change)
            continue

        new_session_id = func.uuid_generate_v4()

        # If there is already one session for this customer which has been
        # updated less than 5 minutes ago, reuse the same session id.
        # Otherwise, generate a new one.
        if key in sessions:
            previous_session_id, previous_status_change = sessions[key]
            if previous_status_change >= hail.last_status_change - datetime.timedelta(minutes=5):
                new_session_id = previous_session_id

        hail.session_id = new_session_id

        # Script feedback
        if not i % 1000:
            print("Hails reviewed up to %s", hail.last_status_change)
            db.session.flush()

        # and keep it for the next round
        sessions[key] = (new_session_id, hail.last_status_change)

    db.session.commit()
