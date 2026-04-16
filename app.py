from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

app = Flask(__name__)
# configuración de la base de datos SQLITE
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///metapython.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)    

#modelo de la tabla log
class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha_y_hora = db.Column(db.DateTime, default=datetime.utcnow)
    texto = db.Column(db.TEXT)

#crear la tsbla si no existe en la base de datos
with app.app_context():
    db.create_all()

    prueba1 = Log(texto='mensaje de prueba 1')
    prueba2 = Log(texto='mensaje de prueba 2')
    db.session.add(prueba1)
    db.session.add(prueba2)
    db.session.commit()

#fumcion para ordenar los registros por fecha y hora
def ordenar_registros_por_fecha(registros):
    return sorted(registros, key=lambda x: x.fecha_y_hora, reverse=True)    

@app.route('/')
def index():
    #obtener todos los regustris de la base de datos
    registros = Log.query.all()
    registros_ordenados = ordenar_registros_por_fecha(registros)
    return render_template('index.html', registros=registros_ordenados)

mensajes_log = []
#funcion para agregar un mensaje al log
def agregar_mensajes_log(texto):
    mensajes_log.append(texto)
    #guardar el mensaje en la base de datos
    nuevo_registro = log(texto=texto)
    db.session.add(nuevo_registro)
    db.session.commit()



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)