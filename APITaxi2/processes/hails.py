import datetime


def change_status(hail, new_status, user=None, reason=None):
    """Set the new status and log it.

    There is no user on automated tasks. The reason is only required on error statuses.
    """
    # func.now() would be better but I get a strange error then:
    # E                   sqlalchemy.orm.exc.StaleDataError: UPDATE statement on table 'hail' expected to update 1 row(s); 0 were matched.
    # Probably the same reason why I was already using datetime in the transition log
    now = datetime.datetime.now(datetime.timezone.utc)

    old_status = hail.status
    hail.status = new_status
    hail.last_status_change = now
    hail.last_update_at = now
    if hail.transition_log is None:
        hail.transition_log = []
    hail.transition_log.append({
        'from_status': old_status,
        'to_status': new_status,
        'timestamp': now.isoformat(),
        'user': user.id if user else None,  # Automated transition
        'reason': reason,
    })
