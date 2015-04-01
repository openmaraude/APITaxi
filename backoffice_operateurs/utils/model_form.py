from flask.ext.wtf import Form
from wtforms_alchemy import model_form_factory
from backoffice_operateurs import db

BaseModelForm = model_form_factory(Form)

class ModelForm(BaseModelForm):
    @classmethod
    def get_session(self):
        return db.session

