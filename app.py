from flask import Flask, render_template, send_from_directory
from models import db, Log, Cita, Consentimiento, Asesor
from webhook import webhook_bp
from asesor import asesor_bp
from config import SECRET_KEY
from datetime import datetime
import os
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:cib2526@localhost:5432/metapython"
)
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)