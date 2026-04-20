import http.client
import json
from config import TOKEN_META, PHONE_NUMBER_ID
from models import agregar_mensajes_log

def enviar_request(data):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer EAAY5YGNZBIz8BRfaVwKmLh3AZCnKu0H0Ru5BaPf5EAMEb6ONhwMrQQkvRR0y9T0x0Pe6vf5DIiQNE2auPMifSd0ZBGXlK5cseNtREExXqgAH5XR6nrHKHWUEpBHemtzhAwwzWNfVWiNo5Au8Y2aRfxaHu6fPbREy785ZCKByq2ilG1WMw2mxuuZCWRURZBdcy8pPQLTNZC5v4YUZBnPKJ1W9J01FXww30M2QZBvhCmLapUZBF1wNL5jPSKpqDuATZApUS2nWkw3dQ9KbuiQnt3Gg4dA'
    }
    connection = http.client.HTTPSConnection('graph.facebook.com')
    try:
        connection.request('POST', f'/v25.0/{PHONE_NUMBER_ID}/messages', json.dumps(data), headers)
        response = connection.getresponse()
        if response.status != 200:
            agregar_mensajes_log(f"Error envio | {response.status} {response.reason}")
    except Exception as e:
           agregar_mensajes_log(f"Error envio: {str(e)}")
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
            "type": "list",
            "body": {"text": "En que podemos ayudarte hoy?"},
            "action": {
                "button": "Ver opciones",
                "sections": [{
                    "title": "Menu principal",
                    "rows": [
                        {"id": "agendar",  "title": "Agendar Cita",  "description": "Programa una nueva cita"},
                        {"id": "cancelar", "title": "Cancelar Cita", "description": "Cancela una cita existente"},
                        {"id": "asesoria", "title": "Asesoria",      "description": "Habla con un asesor"},
                        {"id": "terminar", "title": "Finalizar",     "description": "Terminar la conversacion"}
                    ]
                }]
            }
        }
    }
    enviar_request(data)
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
            DIAS_ES = ["Lunes","Martes","Miercoles","Jueves","Viernes","Sabado","Domingo"]
            MESES_ES = ["","Enero","Febrero","Marzo","Abril","Mayo","Junio",
                       "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
            dias.append(f"{DIAS_ES[dia.weekday()]} {dia.day} de {MESES_ES[dia.month]}")
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