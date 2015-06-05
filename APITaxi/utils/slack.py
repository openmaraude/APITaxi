# -*- coding: utf-8 -*-
from slacker import Slacker
from flask import current_app

def slack():
    if 'SLACK_API_KEY' not in current_app.config or\
            not current_app.config['SLACK_API_KEY']:
        return None
    return Slacker(current_app.config['SLACK_API_KEY'])
