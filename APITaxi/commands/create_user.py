# -*- coding: utf-8 -*-
from ..extensions import user_datastore
from flask.ext.script import prompt_pass
from . import manager
from flask import current_app

def create_user(email, commit=False):
    "Create a user"
#    if not validate_email(email):
#        print("email is not valid")
#        return
    if user_datastore.find_user(email=email):
        print("User has already been created")
        return
    password = prompt_pass("Type a password")
    user = user_datastore.create_user(email=email, password=password)
    if commit:
        current_app.extensions['sqlalchemy'].db.session.commit()
    return user

def create_user_role(email, role_name):
    user = create_user(email)
    role = user_datastore.find_or_create_role(role_name)
    user_datastore.add_role_to_user(user, role)
    current_app.extensions['sqlalchemy'].db.session.commit()

@manager.command
def create_operateur(email):
    create_user_role(email, 'operateur')

@manager.command
def create_moteur(email):
    create_user_role(email, 'moteur')

@manager.command
def create_admin(email):
    create_user_role(email, 'admin')

@manager.command
def create_mairie(email):
    create_user_role(email, 'mairie')

@manager.command
def create_prefecture(email):
    create_user_role(email, 'prefecture')

@manager.command
def create_stats(email):
    create_user_role(email, 'stats')
