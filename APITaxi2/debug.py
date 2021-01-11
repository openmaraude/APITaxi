from flask_login import current_user
from flask import request


class DebugContext:
    """Add debug to an API response.

    Usage:

        >>> debug = DebugContext()
        >>> debug.log('debug-label', data=<python object>)

        # "xxx" is only available for administrators, and is hidden otherwise
        >>> debug.log_admin('debug-admin', data=xxx)

        >>> return debug_ctx.add_to_response(schema.dump(...))

    Then, add ?debug in the querystring to retrieve debug informations.
    """
    def __init__(self):
        self.debug_entries = []

    def debug_enabled(self):
        """Returns True if ?debug is in the querystring."""
        return 'debug' in request.args

    def log(self, label, data=None):
        """Log a debug entry."""
        debug_entry = {'label': label}

        if data is not None:
            debug_entry['data'] = data

        self.debug_entries.append(debug_entry)

    def log_admin(self, label, data=None):
        """Log entry, but hide data if current user is not administrator."""
        if not current_user.has_role('admin'):
            self.log(label, data='<hidden, only visible for administrators>')
            return

        self.log(label, data=data)

    def add_to_response(self, response):
        """Response is expected to be a dictionary. Add the key "debug" with
        the debug entries if debug is enabled."""
        if self.debug_enabled():
            response['debug'] = self.debug_entries
        return response
