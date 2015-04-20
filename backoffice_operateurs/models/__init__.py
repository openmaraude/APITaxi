# -*- coding: utf8 -*-
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy(session_options={"autoflush":False})
from hail import Hail, Customer
from taxis import Taxi
