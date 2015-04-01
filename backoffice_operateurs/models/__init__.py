# -*- coding: utf8 -*-
from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy(session_options={"autoflush":False})
