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
        entry = req.get('entry', [])
        if not entry:
            return jsonify({'message': 'EVENT_RECEIVED'})

        changes = entry[0].get('changes', [])
        if not changes:
            return jsonify({'message': 'EVENT_RECEIVED'})

        value = changes[0].get('value', {})
        objeto_messages = value.get('messages', [])

        if objeto_messages:
            mensaje = objeto_messages[0]
            numero = mensaje['from']
            tipo = mensaje.get('type')

            # Usuario envía un botón interactivo
            if tipo == 'interactive':
                interactive = mensaje.get('interactive', {})
                button_reply = interactive.get('button_reply', {})
                opcion_id = button_reply.get('id', '')
                manejar_opcion(numero, opcion_id)

            # Usuario envía texto (respondiendo datos)
            elif tipo == 'text':
                texto = mensaje['text']['body']
                agregar_mensajes_log(f"Mensaje de {numero}: {texto}")
                manejar_flujo_datos(numero, texto)

        return jsonify({'message': 'EVENT_RECEIVED'})
    except Exception as e:
        agregar_mensajes_log(f"Error: {str(e)}")
        return jsonify({'message': 'EVENT_RECEIVED'})


# MANEJO DEL FLUJO

def manejar_opcion(numero, opcion_id):
    """Cuando el usuario toca un botón del menú"""
    if opcion_id == 'agendar':
        sesiones[numero] = {'flujo': 'agendar', 'paso': 'nombre'}
        enviar_texto(numero, "📅 *Agendar Cita*\n\nPor favor escribe tu *nombre y apellido*:")

    elif opcion_id == 'confirmar':
        sesiones[numero] = {'flujo': 'confirmar', 'paso': 'nombre'}
        enviar_texto(numero, "✅ *Confirmar Cita*\n\nPor favor escribe tu *nombre y apellido*:")

    elif opcion_id == 'asesoria':
        sesiones[numero] = {'flujo': 'asesoria', 'paso': 'nombre'}
        enviar_texto(numero, "💬 *Asesoría*\n\nPor favor escribe tu *nombre y apellido*:")


def manejar_flujo_datos(numero, texto):
    """Maneja los pasos de recolección de datos"""
    if numero not in sesiones:
        # Si no hay sesión activa, mostrar menú
        enviar_menu(numero)
        return

    sesion = sesiones[numero]
    paso = sesion.get('paso')

    if paso == 'nombre':
        sesiones[numero]['nombre'] = texto
        sesiones[numero]['paso'] = 'documento'
        enviar_texto(numero, "🪪 Ahora escribe tu *número de documento*:")

    elif paso == 'documento':
        sesiones[numero]['documento'] = texto
        sesiones[numero]['paso'] = 'telefono'
        enviar_texto(numero, "📞 Por último, escribe tu *número de teléfono*:")

    elif paso == 'telefono':
        sesiones[numero]['telefono'] = texto
        sesiones[numero]['paso'] = 'completado'

        # Guardar en log
        flujo = sesiones[numero]['flujo']
        nombre = sesiones[numero]['nombre']
        documento = sesiones[numero]['documento']
        agregar_mensajes_log(
            f"[{flujo.upper()}] Nombre: {nombre} | Doc: {documento} | Tel: {texto} | WhatsApp: {numero}"
        )

        # Confirmar al usuario
        enviar_texto(numero,
            f"✅ ¡Gracias *{nombre}*! Tus datos han sido registrados.\n\n"
            f"📋 *Resumen:*\n"
            f"• Nombre: {nombre}\n"
            f"• Documento: {documento}\n"
            f"• Teléfono: {texto}\n\n"
            f"Pronto te contactaremos. 😊"
        )

        # Limpiar sesión y mostrar menú de nuevo
        del sesiones[numero]
        enviar_menu(numero)



# FUNCIONES DE ENVÍO


def enviar_menu(numero):
    """Envía el menú principal con botones"""
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": "👋 ¡Bienvenido! ¿En qué podemos ayudarte hoy?"
            },
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "agendar",   "title": "📅 Agendar Cita"}},
                    {"type": "reply", "reply": {"id": "confirmar", "title": "✅ Confirmar Cita"}},
                    {"type": "reply", "reply": {"id": "asesoria",  "title": "💬 Recibir Asesoría"}}
                ]
            }
        }
    }
    enviar_request(data)


def enviar_texto(numero, mensaje):
    """Envía un mensaje de texto simple"""
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": mensaje
        }
    }
    enviar_request(data)


def enviar_request(data):
    """Realiza la petición HTTP a la API de Meta"""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer EAAY5YGNZBIz8BROZAu6p5Rf47pYtjvlZAYUtPkoDksDXYN4gBkx96ZBmvMuJg4vBDQrZCmaDAsARL3A6XReXmnYG84kfsMwfZCH1IFFAsXlFzz1NerVd6HMm6uv63CrcdSaviknNivnIbAICzwTapJl4OKFZANv8E2f3GDbMVMYKj3cgX46hKFLZB3KwWpUvJjBKZBFcoyYlxVcPgyIgLIdlcV7aTRw0leAZCPBZCgbM9DU1W9fqcWLd04P4fzkdhgoyBg1yo2btCVZAiA2e4pBS0rkW0AZDZD'
    }
    connection = http.client.HTTPSConnection('graph.facebook.com')
    try:
        connection.request('POST', f'/v25.0/{PHONE_NUMBER_ID}/messages', json.dumps(data), headers)
        response = connection.getresponse()
        agregar_mensajes_log(f"Respuesta Meta: {response.status} {response.reason}")
    except Exception as e:
        agregar_mensajes_log(f"Error al enviar: {str(e)}")
    finally:
        connection.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
