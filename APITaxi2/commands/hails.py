import datetime
import uuid

from flask import Blueprint, current_app

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
    for i, (hail_id, session_id, last_status_change, customer_id, added_by_id) in enumerate(db.session.query(
        Hail.id, Hail.session_id, Hail.last_status_change, Hail.customer_id, Hail.added_by_id
    ).order_by(
        Hail.last_status_change
    )):
        # Customer IDs are unique to the search engine were they are registered
        key = (customer_id, added_by_id)

        # If this hail was already assigned a session ID, just record it
        if session_id:
            sessions[key] = (session_id, last_status_change)
            continue

        session_id = None

        # If there is already one session for this customer which has been
        # updated less than 5 minutes ago, reuse the same session id.
        # Otherwise, generate a new one.
        if key in sessions:
            previous_session_id, previous_status_change = sessions[key]
            if previous_status_change >= last_status_change - datetime.timedelta(minutes=5):
                session_id = previous_session_id
            else:
                session_id = uuid.uuid4()

        db.session.query(Hail).filter(
            Hail.id == hail_id
        ).update(
            {'session_id': session_id}
        )
        db.session.commit()

        # Script feedback
        if not i % 1000:
            current_app.logger.info("Hails reviewed up to %s", last_status_change)

        # and keep it for the next round
        sessions[key] = (session_id, last_status_change)
