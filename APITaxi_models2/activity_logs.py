from sqlalchemy import Table
from sqlalchemy.dialects import postgresql

from . import db


class ActivityLog(db.Model):
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    time = db.Column(db.DateTime, primary_key=True)
    resource = db.Column(db.String, nullable=False)
    resource_id = db.Column(db.String, nullable=False)
    action = db.Column(db.String, nullable=False)
    extra = db.Column(postgresql.JSONB)
