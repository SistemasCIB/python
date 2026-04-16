from flask import Flask,request, render_template, jsonify 
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


TOKEN_ANDERCODE = "ANDERCODE"
@app.route('/webhook',methods=['GET','POST'])
def webhook():
    if request.method == 'GET':
        challenge = verificar_token(request)
        return challenge
    elif request.method == 'POST':
        response = recibir_mensaje(request)
        return response

def verificar_token(request):
    token = request.args.get('hud.verification_token')
    challenge = request.args.get('hud.challenge')
    if challenge and token == TOKEN_ANDERCODE:
        return challenge
    else:
        return jsonify({'error': 'Token de verificación no válido'}), 401
  

def recibir_mensaje(request):
    req = request.get_json()
    agregar_mensajes_log(req)
    
    return jsonify({'status': 'Mensaje recibido correctamente'})
 
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)