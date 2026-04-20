#solo funciones de envio de mensajes
import http.client
import json
from config import TOKEN_META, PHONE_NUMBER_ID

def enviar_request(data):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer EAAY5YGNZBIz8BRcwoZCblE26DD5JD6hdAthLx3T1rOmjSReLpPJGNH8FJ2lM3jfBZAkb4Lb9fv8XoNJWlpxH94ZB4w9MYBXKpX7c1nBpsJt2RlSMT542MEmkRlHGrNZCIqSOZC7UcxEZBQcms0t3lKMPv7fglGyf7iRWpmq2zZCiBpvwZCZCVJZBqyMx1UJoqTIIZASkNQeJFxu00qBL995k5ZC718XA5siV1GwdohU7wSRnsSgzlXdKFmxceZCaYZCaLth5PeuCUwB4kyCCSnUBzLP0Vb3RQZDZD'
    }
    connection = http.client.HTTPSConnection('graph.facebook.com')
    try:
        connection.request('POST', f'/v25.0/{PHONE_NUMBER_ID}/messages', json.dumps(data), headers)
        response = connection.getresponse()
        from models import db, Log
        nuevo_log = Log(texto=f"Meta: {response.status} {response.reason}")
        db.session.add(nuevo_log)
        db.session.commit()
    except Exception as e:
        print(f"Error al enviar: {str(e)}")
    finally:
        connection.close()

def enviar_texto(numero, mensaje):
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "text",
        "text": {"preview_url": False, "body": mensaje}
    }
    enviar_request(data)

def enviar_menu(numero):
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "En que podemos ayudarte?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "agendar",  "title": "Agendar Cita"}},
                    {"type": "reply", "reply": {"id": "cancelar", "title": "Cancelar Cita"}},
                    {"type": "reply", "reply": {"id": "asesoria", "title": "Asesoria"}}
                ]
            }
        }
    }
    enviar_request(data)

def enviar_bienvenida(numero):
    from config import URL_BASE
    enviar_texto(numero,
        "Bienvenido a la Corporacion para Investigaciones Biologicas - CIB\n\n"
        "Antes de continuar, por favor lee nuestra Politica de Tratamiento "
        "y Proteccion de Datos Personales:\n\n"
        f"{URL_BASE}/politica\n\n"
        "Para continuar necesitamos tu autorizacion:"
    )
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "Autorizas el tratamiento de tus datos personales segun la Ley 1581 de 2012?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "acepto_datos",   "title": "Si, acepto"}},
                    {"type": "reply", "reply": {"id": "no_acepto_datos","title": "No acepto"}}
                ]
            }
        }
    }
    enviar_request(data)

def mostrar_fechas_disponibles(numero, sesiones):
    from datetime import datetime, timedelta
    dias = []
    dia = datetime.now() + timedelta(days=1)
    while len(dias) < 3:
        if dia.weekday() < 5:
            dias.append(dia.strftime("%A %d de %B"))
        dia += timedelta(days=1)

    botones = []
    for i, d in enumerate(dias):
        botones.append({
            "type": "reply",
            "reply": {"id": f"fecha_{i+1}", "title": d[:20]}
        })
    sesiones[numero]['fechas'] = {f"fecha_{i+1}": d for i, d in enumerate(dias)}

    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "Selecciona una fecha disponible:"},
            "action": {"buttons": botones}
        }
    }
    enviar_request(data)