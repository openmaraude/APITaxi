from backoffice_operateurs import app, db
from backoffice_operateurs.forms import taxis as taxis_forms
from backoffice_operateurs.models import taxis as taxis_models
from flask import render_template, request, redirect, url_for, abort
from flask.ext.security import login_required

@app.route('/conducteurs')
@app.route('/conducteurs/')
@login_required
def conducteurs_list():
    page = int(request.args.get('page')) if 'page' in request.args else 1
    return render_template('lists/conducteurs.html',
        conducteur_list=taxis_models.Conducteur.query.paginate(page))


@app.route('/conducteur/create', methods=['GET', 'POST'])
def conducteur_create():
    form = taxis_forms.ConducteurCreateForm()
    if request.method == "POST" and form.validate():
        conducteur = taxis_models.Conducteur()
        form.populate_obj(conducteur)
        db.session.add(conducteur)
        db.session.commit()
        return redirect(url_for('conducteurs_list'))
    return render_template('forms/conducteur.html', form=form,
        form_method="POST", submit_value="Creer")

@app.route('/conducteur/update', methods=['GET', 'POST'])
@login_required
def conducteur_update():
    if not request.args.get("id"):
        abort(404)
    conducteur = taxis_models.Conducteur.query.get(request.args.get("id"))
    if not conducteur:
        abort(404)
    form = taxis_forms.ConducteurUpdateForm(obj=conducteur)
    if request.method == "POST":
        form.populate_obj(conducteur)
        if form.validate():
            db.session.commit()
            return redirect(url_for('conducteurs_list'))

    return render_template('forms/conducteur.html', form=form,
        form_method="POST", submit_value="Modifier")


@app.route('/conducteur/delete')
@login_required
def conducteur_delete():
    if not request.args.get("id"):
        abort(404)
    conducteur = taxis_models.Conducteur.query.get(request.args.get("id"))
    if not conducteur:
        abort(404)
    db.session.delete(conducteur)
    db.session.commit()
    return redirect(url_for("conducteurs_list"))

