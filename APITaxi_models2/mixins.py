from . import db


class HistoryMixin:
    added_at = db.Column(db.DateTime, nullable=False)
    added_via = db.Column(db.Enum('form', 'api', name='sources'), nullable=False)
    source = db.Column(db.String(255), nullable=False)
    last_update_at = db.Column(db.DateTime)
