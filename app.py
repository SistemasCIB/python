from flask import Flask, render_template, send_from_directory, redirect
from models import db, Log, Cita, Consentimiento, Asesor
from webhook import webhook_bp
from asesor import asesor_bp
from config import SECRET_KEY, TOKEN_META
from datetime import datetime
import os
import requests as req_lib
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cib.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = SECRET_KEY

db.init_app(app)
app.register_blueprint(webhook_bp)
app.register_blueprint(asesor_bp)

with app.app_context():
    db.create_all()
    # Crear asesor por defecto si no existe
    if not Asesor.query.filter_by(usuario='admin').first():
        asesor = Asesor(usuario='admin', nombre='Administrador')
        asesor.set_password('cib2025')
        db.session.add(asesor)
        db.session.commit()
        print("Asesor creado: admin / cib2025")

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

def ordenar_registros_por_fecha(registros):
    return sorted(registros, key=lambda x: x.fecha_y_hora, reverse=True)

@app.route('/')
def index():
    registros = ordenar_registros_por_fecha(Log.query.all())
    citas = Cita.query.order_by(Cita.creada_en.desc()).all()
    consentimientos = Consentimiento.query.order_by(Consentimiento.fecha.desc()).all()
    return render_template('index.html',
        registros=registros,
        citas=citas,
        consentimientos=consentimientos
    )

@app.route('/politica')
def politica():
    return send_from_directory('static', 'politica_datos.pdf')


@app.route('/asesor/orden/<int:cita_id>')
def ver_orden(cita_id):
    cita = Cita.query.get_or_404(cita_id)

    if not cita.orden_medica:
        return "Esta cita no tiene orden médica.", 404

    # 1. Consultar la URL real del archivo a Meta
    headers = {"Authorization": f"Bearer {TOKEN_META}"}
    r = req_lib.get(
        f"https://graph.facebook.com/v25.0/{cita.orden_medica}",
        headers=headers
    )

    if r.status_code != 200:
        return f"Error consultando archivo a Meta: {r.text}", 500

    url_archivo = r.json().get("url")

    if not url_archivo:
        return "No se pudo obtener la URL del archivo.", 500

    # 2. Redirigir al asesor al archivo real
    return redirect(url_archivo)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)