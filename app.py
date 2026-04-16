from flask import Flask,request, render_template, jsonify 
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import http.client

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
    nuevo_registro = Log(texto=texto)
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
    print("ARGS:", request.args) 
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if challenge and token == TOKEN_ANDERCODE:
        return challenge
    else:
        return jsonify({'error': 'Token invalido'}), 401

def recibir_mensaje(request):

    try:
        req = request.get_json()
        entry = req.get('entry', [0])
        changes = entry('changes', [0])
        value = changes ['value']  
        objeto_messages = value['messages']  

        if objeto_messages:
            messages = objeto_messages[0]
            if "type" in messages:
               tipo = messages["type"]
               if tipo == "interactive":
                   return 0
               if "text" in messages:
                   text= messages["text"]["body"]
                   numero = messages["from"]
                   agregar_mensajes_log(f"Mensaje recibido: {text} de {numero}")
                   enviar_mensajes(text,numero)
        return jsonify({'message': 'EVENT_RECEIVED'})
    except Exception as e:
        return jsonify({'message': 'EVENT_RECEIVED'})                   

def enviar_mensajes(texto,number):
        texto = texto.lower()
        if "hola" in texto:
            data={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": number,
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": "Hola, gracias por tu mensaje. ¿En qué puedo ayudarte?"

                }
            }
        else:
            data={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": number,
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": "no entiendo tu mensaje, por favor intenta con otra cosa"
                    

                }
            }
    
        data = json.dumps(data)
       
        headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer EAAY5YGNZBIz8BROyfXRU76i2Xwg8QVulAahf8mEqZBqBZCiUp7oDaZAtxgv56VHeMaAxZBFZB4ZA2K1QSo8ZC3PWU6aq93ZCodrJKWOF7CZC5fESfbjsZBOIoJHb6wykIn10R5LzoB0ly88w2kWcacJxVrrX7sePj7DbjNrK1zDZBnQFAxWss2DnaNEHoQ15CmQZAech8ZCyqssuhfzy4AWZCsS2z5XZC9ZCow2vBh2LKSs1oYWWcna0m8KrbBPEdQObyVBSZCzq8wKBaHc9IkqB2vhcaDqpD4wAZDZD'
        }
        connection = http.client.HTTPSConnection('graph.facebook.com')
        
        try:
            connection.request('POST', '/v25.0/1112533955267866/messages', data, headers)
            response = connection.getresponse()
            print(response.status, response.reason)
        
        except Exception as e:
            agregar_mensajes_log(json.dumps(e)) 
        
        finally: 
            connection.close()      

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)