from flask import Flask, render_template, send_from_directory
from models import db, Log
from webhook import webhook_bp
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///metapython.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
app.register_blueprint(webhook_bp)

with app.app_context():
    db.create_all()

def ordenar_registros_por_fecha(registros):
    return sorted(registros, key=lambda x: x.fecha_y_hora, reverse=True)

@app.route('/')
def index():
    registros = Log.query.all()
    return render_template('index.html', registros=ordenar_registros_por_fecha(registros))

@app.route('/politica')
def politica():
    return send_from_directory('static', 'politica_datos.pdf')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)