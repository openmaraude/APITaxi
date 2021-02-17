import datetime


def change_status(hail, new_status, user=None, reason=None):
    """Set the new status and log it.

    There is no user on automated tasks. The reason is only required on error statuses.
    """
    old_status = hail.status
    hail.status = new_status
    if hail.transition_log is None:
        hail.transition_log = []
    hail.transition_log.append({
        'from_status': old_status,
        'to_status': new_status,
        # Time of the Postgres server would be better
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'user': user.id if user else None,  # Automated transition
        'reason': reason,
    })
