# -*- coding: utf-8 -*-
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy(session_options={"autoflush":False})
from .security import User
from .vehicle import Vehicle, Model, Constructor, VehicleDescription
from .hail import Hail, Customer
from .taxis import Taxi
