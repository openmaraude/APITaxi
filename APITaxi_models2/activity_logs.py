from sqlalchemy import Table
from sqlalchemy.dialects import postgresql

from . import db


# Low-level table without a primary key, not usable with the ORM
activity_log = Table(
    "activity_log",
    db.metadata,
    db.Column("time", db.DateTime, nullable=False),
    db.Column("resource", db.String, nullable=False),
    db.Column("resource_id", db.String, nullable=False),
    db.Column("action", db.String, nullable=False),
    db.Column("extra", postgresql.JSONB),
)
