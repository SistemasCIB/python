#rutas Flask
from flask import Blueprint, request, jsonify
from models import db, Log
from flujos import manejar_boton, manejar_texto, agregar_mensajes_log
from config import TOKEN_ANDERCODE
import json

webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return verificar_token(request)
    elif request.method == 'POST':
        return recibir_mensaje(request)

def verificar_token(req):
    token = req.args.get('hub.verify_token')
    challenge = req.args.get('hub.challenge')
    if challenge and token == TOKEN_ANDERCODE:
        return challenge
    return jsonify({'error': 'Token invalido'}), 401
    
def agregar_mensajes_log(texto):  # 👈 definida aquí directamente
    nuevo_registro = Log(texto=str(texto))
    db.session.add(nuevo_registro)
    db.session.commit()

def recibir_mensaje(req):
    try:
        data = req.get_json()
        agregar_mensajes_log(f"Request: {json.dumps(data)}")

        entry = data.get('entry', [])
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

            if tipo == 'interactive':
                button_reply = mensaje.get('interactive', {}).get('button_reply', {})
                manejar_boton(numero, button_reply.get('id', ''))

            elif tipo == 'text':
                texto = mensaje['text']['body']
                agregar_mensajes_log(f"Mensaje de {numero}: {texto}")
                manejar_texto(numero, texto)

        return jsonify({'message': 'EVENT_RECEIVED'})
    except Exception as e:
        agregar_mensajes_log(f"Error: {str(e)}")
        return jsonify({'message': 'EVENT_RECEIVED'})