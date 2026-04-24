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
                        {"id": "resultados", "title": "Consultar Resultados", "description": "Consulta el estado o entrega de tus resultados"},
                        {"id": "otros", "title": "Otros servicios", "description": "Informacion sobre nuestros servicios"},
                        {"id": "terminar", "title": "Finalizar",     "description": "Terminar la conversacion"}
                    ]
                }]
            }
        }
    }
    enviar_request(data)

def enviar_bienvenida(numero):
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": (
                    "👋¡Bienvenido(a) a la Corporación para Investigaciones Biológicas (CIB)!\n\n "
                    "Somos un laboratorio especializado en diagnóstico, investigación, servicios en salud y otros servicios 🧪\n\n"
                    "Estamos aquí para ayudarte con:\n"
                    "- Agendar citas\n"
                    "- Consulta de resultados\n"
                    "- Información sobre nuestros servicios\n\n"
                    "📌 Para brindarte una mejor atención, sigue las opciones que te indicaremos a continuación.\n\n"
                    "¡Gracias por confiar en nosotros!💙\n"
                    "Antes de continuar, por favor indícanos si eres paciente o cliente:"
                )
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "soy_paciente",
                            "title": "Paciente: Persona que necesita un examen, quiere agendar una cita o consultar resultados para sí mismo o un familiar."
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "soy_cliente",
                            "title": "Cliente: Empresa o profesional (IPS, médico, laboratorio, aseguradora) que solicita información, envía muestras o tiene convenio con nosotros."
                        }
                    }
                ]
            }
        }
    }

    enviar_request(data)
    
def enviar_politica_datos(numero):
    from config import URL_BASE

    enviar_texto(
        numero,
        "📄 Protección de datos personale\n\n "
        "Tus datos serán tratados conforme a la Ley 1581 de 2012 y el Decreto 1377 de 2013.\n"
        "Serán usados únicamente para la prestación de nuestros servicios de salud.\n\n"
        "Consulta nuestra política aquí:\n"
         f" {URL_BASE}/politica"
    )

    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": "Autorizas el tratamiento de tus datos personales?"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "acepto_datos",
                            "title": "Si acepto"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "no_acepto_datos",
                            "title": "No acepto"
                        }
                    }
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

def mostrar_horas_disponibles(numero):

    horas = [
        "07:00", "08:00", "09:00", "10:00",
        "11:00", "12:00", "13:00", "14:00",
        "15:00", "16:00"
    ]

    botones = []

    for i, h in enumerate(horas):
        botones.append({
            "type": "reply",
            "reply": {
                "id": f"hora_{i+1}",
                "title": h
            }
        })

    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "Selecciona una hora disponible:"},
            "action": {"buttons": botones[:3]}
        }
    }

    enviar_request(data) 
    
def enviar_tipo_documento(numero):
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "Selecciona el tipo de documento de identificacion:"},
            "action": {
                "button": "Ver tipos",
                "sections": [{
                    "title": "Tipo de documento",
                    "rows": [
                        {"id": "tdoc_CC",   "title": "CC",  "description": "Cedula de ciudadania"},
                        {"id": "tdoc_TI",   "title": "TI",  "description": "Tarjeta de identidad"},
                        {"id": "tdoc_CE",   "title": "CE",  "description": "Cedula de extranjeria"},
                        {"id": "tdoc_PPT",  "title": "PPT", "description": "Permiso de proteccion temporal"},
                        {"id": "tdoc_RC",   "title": "RC",  "description": "Registro civil"},
                        {"id": "tdoc_Otro", "title": "Otro","description": "Otro tipo de documento"}
                    ]
                }]
            }
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