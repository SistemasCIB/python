from flask import Flask, request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import http.client

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///metapython.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha_y_hora = db.Column(db.DateTime, default=datetime.utcnow)
    texto = db.Column(db.TEXT)

with app.app_context():
    db.create_all()

def ordenar_registros_por_fecha(registros):
    return sorted(registros, key=lambda x: x.fecha_y_hora, reverse=True)

@app.route('/')
def index():
    registros = Log.query.all()
    registros_ordenados = ordenar_registros_por_fecha(registros)
    return render_template('index.html', registros=registros_ordenados)

mensajes_log = []

def agregar_mensajes_log(texto):
    mensajes_log.append(texto)
    nuevo_registro = Log(texto=str(texto))
    db.session.add(nuevo_registro)
    db.session.commit()

TOKEN_ANDERCODE = "ANDERCODE"
TOKEN_META = "aquí_tu_token_de_meta"  # 👈 pon tu token real aquí

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return verificar_token(request)
    elif request.method == 'POST':
        return recibir_mensaje(request)

def verificar_token(request):
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if challenge and token == TOKEN_ANDERCODE:
        return challenge
    return jsonify({'error': 'Token invalido'}), 401

def recibir_mensaje(request):
    try:
        req = request.get_json()
        agregar_mensajes_log(f"Request recibido: {json.dumps(req)}")  # 👈 log del request

        entry = req.get('entry', [])
        if not entry:
            return jsonify({'message': 'EVENT_RECEIVED'})

        changes = entry[0].get('changes', [])  # ✅ corregido
        if not changes:
            return jsonify({'message': 'EVENT_RECEIVED'})

        value = changes[0].get('value', {})
        objeto_messages = value.get('messages', [])

        if objeto_messages:
            messages = objeto_messages[0]
            tipo = messages.get('type')

            if tipo == 'interactive':
                return jsonify({'message': 'EVENT_RECEIVED'})

            if tipo == 'text':
                text = messages["text"]["body"]
                numero = messages["from"]
                agregar_mensajes_log(f"Mensaje de {numero}: {text}")  # ✅ guarda en BD
                enviar_mensajes(text, numero)

        return jsonify({'message': 'EVENT_RECEIVED'})
    except Exception as e:
        agregar_mensajes_log(f"Error: {str(e)}")  # ✅ guarda errores también
        return jsonify({'message': 'EVENT_RECEIVED'})

def enviar_mensajes(texto, number):
    texto = texto.lower()
    if "hola" in texto:
        body = "Hola, gracias por tu mensaje. ¿En qué puedo ayudarte?"
    else:
        body = "No entiendo tu mensaje, por favor intenta con otra cosa."

    data = json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": body
        }
    })

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer EAAY5YGNZBIz8BROyfXRU76i2Xwg8QVulAahf8mEqZBqBZCiUp7oDaZAtxgv56VHeMaAxZBFZB4ZA2K1QSo8ZC3PWU6aq93ZCodrJKWOF7CZC5fESfbjsZBOIoJHb6wykIn10R5LzoB0ly88w2kWcacJxVrrX7sePj7DbjNrK1zDZBnQFAxWss2DnaNEHoQ15CmQZAech8ZCyqssuhfzy4AWZCsS2z5XZC9ZCow2vBh2LKSs1oYWWcna0m8KrbBPEdQObyVBSZCzq8wKBaHc9IkqB2vhcaDqpD4wAZDZD'  # ✅ token correcto con espacio
    }

    connection = http.client.HTTPSConnection('graph.facebook.com')
    try:
        connection.request('POST', '/v25.0/1112533955267866/messages', data, headers)
        response = connection.getresponse()
        agregar_mensajes_log(f"Respuesta Meta: {response.status} {response.reason}")
    except Exception as e:
        agregar_mensajes_log(f"Error al enviar: {str(e)}")
    finally:
        connection.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)