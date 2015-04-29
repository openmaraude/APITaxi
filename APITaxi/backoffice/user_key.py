from flask.ext.security import login_required, current_user
from flask import Blueprint

mod = Blueprint('user_key', __name__)

@mod.route('/user_key')
@login_required
def user_key():
    return render_template('user.html', user=current_user)
