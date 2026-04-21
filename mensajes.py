import http.client
import json
from config import TOKEN_META, PHONE_NUMBER_ID, LINK_ASESOR, HORARIO_INICIO, HORARIO_FIN, REQUISITOS
from models import agregar_mensajes_log

def enviar_request(data):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer EAAY5YGNZBIz8BRXwA8UTEa16UrRYq3UZAoinyvHxjyXzLsaGAfimXp6qWUD4ZBlMOMywI3nTV3Oet56Ov2L697IbfXA6l8FOwpNvUoXtM0iwS8INTFrq7mpEKBB9rLq3kJXgzRQlv9Ffd2q8ZCRZC8XVYR0opra2ydz68qEfHmCBs0F9ie4AcYtYEGEpDEQZDZD'
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
                    {"type": "reply", "reply": {"id": "acepto_datos",    "title": "Si, acepto"}},
                    {"type": "reply", "reply": {"id": "no_acepto_datos", "title": "No acepto"}}
                ]
            }
        }
    }
    enviar_request(data)

def enviar_tipo_cita(numero):
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "Que tipo de cita necesitas?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "tipo_presencial", "title": "Presencial"}},
                    {"type": "reply", "reply": {"id": "tipo_domicilio",  "title": "Domicilio"}}
                ]
            }
        }
    }
    enviar_request(data)

def enviar_requisitos(numero, tipo):
    requisitos = REQUISITOS.get(tipo, [])
    lista = "\n".join([f"- {r}" for r in requisitos])
    horario = f"Horario de atencion: Lunes a viernes de {HORARIO_INICIO}am a {HORARIO_FIN}pm"
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": f"Para una cita {tipo} necesitas:\n\n{lista}\n\n{horario}\n\nCumples con estos requisitos?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "cumple_si", "title": "Si, cumplo"}},
                    {"type": "reply", "reply": {"id": "cumple_no", "title": "No cumplo"}}
                ]
            }
        }
    }
    enviar_request(data)

def mostrar_fechas_disponibles(numero, sesiones):
    from datetime import datetime, timedelta
    DIAS_ES = ["Lunes","Martes","Miercoles","Jueves","Viernes","Sabado","Domingo"]
    MESES_ES = ["","Enero","Febrero","Marzo","Abril","Mayo","Junio",
                "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

    dias = []
    dia = datetime.now() + timedelta(days=1)
    while len(dias) < 3:
        if dia.weekday() < 5:
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

def enviar_fuera_horario(numero):
    from config import HORARIO_INICIO, HORARIO_FIN
    enviar_texto(numero,
        f"Nuestros asesores estan disponibles de lunes a viernes "
        f"de {HORARIO_INICIO}am a {HORARIO_FIN}pm.\n\n"
        f"Por favor contactanos en ese horario. Gracias!"
    )