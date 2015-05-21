# -*- coding: utf-8 -*-
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy(session_options={"autoflush":False})
from vehicle import Vehicle, Model, Constructor
from hail import Hail, Customer
from taxis import Taxi
