from flask import Flask, request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json
import http.client

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///metapython.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ─────────────────────────────────────────────
# MODELOS
# ─────────────────────────────────────────────

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha_y_hora = db.Column(db.DateTime, default=datetime.utcnow)
    texto = db.Column(db.TEXT)

class Cita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    documento = db.Column(db.String(50))
    telefono = db.Column(db.String(20))
    fecha_cita = db.Column(db.String(50))
    numero_whatsapp = db.Column(db.String(20))
    estado = db.Column(db.String(20), default='activa')  # activa / cancelada
    creada_en = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# ─────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────

def ordenar_registros_por_fecha(registros):
    return sorted(registros, key=lambda x: x.fecha_y_hora, reverse=True)

def agregar_mensajes_log(texto):
    nuevo_registro = Log(texto=str(texto))
    db.session.add(nuevo_registro)
    db.session.commit()

def obtener_proximos_dias_habiles():
    """Genera los próximos 3 días hábiles (lunes a viernes)"""
    dias = []
    dia = datetime.now() + timedelta(days=1)
    while len(dias) < 3:
        if dia.weekday() < 5:  # 0=lunes, 4=viernes
            dias.append(dia.strftime("%A %d de %B"))  # Ej: Lunes 20 de enero
        dia += timedelta(days=1)
    return dias

# ─────────────────────────────────────────────
# SESIONES (estado por usuario)
# ─────────────────────────────────────────────
sesiones = {}

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ────────────────────────────────────────────
TOKEN_ANDERCODE = "ANDERCODE"
TOKEN_META = "EAAY5YGNZBIz8BRAjKyKpEXAuVOPyfYNitaGXr1Ae5bSnu5LZBXDhUQ9pjUR81KSO4OJ5Imk5yOPURdMJzdCb961WrcpdHqDjbMrOEtORhU28bU03q8JfRfD1MKkQvZB26iVh2ey604MPpaaEfMJJLZCRZBdwVGLLFfO7pcHBm0cVisfJI1oZB5wbdFwAqqvoaxJNVAT46WdLrbX2dVgVdqHZBByd24HwNXpTqr02YbjaCkjs1twOl7AZBhjVZBjLrLuyvVOM3417FTDiZCZC6vMt144"
PHONE_NUMBER_ID = "1112533955267866"
NUMERO_ASESOR = "573001234567" 
# ─────────────────────────────────────────────
# RUTAS
# ─────────────────────────────────────────────

@app.route('/')
def index():
    registros = Log.query.all()
    registros_ordenados = ordenar_registros_por_fecha(registros)
    return render_template('index.html', registros=registros_ordenados)

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

# ─────────────────────────────────────────────
# RECIBIR MENSAJE
# ─────────────────────────────────────────────

def recibir_mensaje(request):
    try:
        req = request.get_json()
        agregar_mensajes_log(f"Request: {json.dumps(req)}")

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

            if tipo == 'interactive':
                interactive = mensaje.get('interactive', {})
                button_reply = interactive.get('button_reply', {})
                opcion_id = button_reply.get('id', '')
                manejar_boton(numero, opcion_id)

            elif tipo == 'text':
                texto = mensaje['text']['body']
                agregar_mensajes_log(f"Mensaje de {numero}: {texto}")
                manejar_texto(numero, texto)

        return jsonify({'message': 'EVENT_RECEIVED'})
    except Exception as e:
        agregar_mensajes_log(f"Error: {str(e)}")
        return jsonify({'message': 'EVENT_RECEIVED'})

# ─────────────────────────────────────────────
# MANEJO DE BOTONES
# ─────────────────────────────────────────────

def manejar_boton(numero, opcion_id):
    # Menú principal
    if opcion_id == 'agendar':
        sesiones[numero] = {'flujo': 'agendar', 'paso': 'nombre'}
        enviar_texto(numero, "📅 *Agendar Cita*\n\nPor favor escribe tu *nombre completo*:")

    elif opcion_id == 'cancelar':
        sesiones[numero] = {'flujo': 'cancelar', 'paso': 'documento'}
        enviar_texto(numero, "❌ *Cancelar Cita*\n\nEscribe tu *número de documento* para buscar tu cita:")

    elif opcion_id == 'asesoria':
        enviar_texto(numero,
            f"💬 *Asesoría*\n\n"
            f"Te comunico con uno de nuestros asesores:\n\n"
            f"📞 *{NUMERO_ASESOR}*\n\n"
            f"¡Estará feliz de ayudarte! 😊"
        )
        enviar_menu(numero)

    # Selección de fecha
    elif opcion_id.startswith('fecha_'):
        fecha_elegida = opcion_id.replace('fecha_', '').replace('_', ' ')
        confirmar_cita(numero, fecha_elegida)

    # Confirmar cancelación
    elif opcion_id == 'si_cancelar':
        ejecutar_cancelacion(numero)

    elif opcion_id == 'no_cancelar':
        del sesiones[numero]
        enviar_texto(numero, "✅ Tu cita *no fue cancelada*. ¡Hasta pronto!")
        enviar_menu(numero)

# ─────────────────────────────────────────────
# MANEJO DE TEXTO (recolección de datos)
# ─────────────────────────────────────────────

def manejar_texto(numero, texto):
    if numero not in sesiones:
        enviar_menu(numero)
        return

    sesion = sesiones[numero]
    flujo = sesion.get('flujo')
    paso = sesion.get('paso')

    # ── FLUJO AGENDAR ──
    if flujo == 'agendar':
        if paso == 'nombre':
            sesiones[numero]['nombre'] = texto
            sesiones[numero]['paso'] = 'documento'
            enviar_texto(numero, "🪪 Escribe tu *número de documento de identidad*:")

        elif paso == 'documento':
            sesiones[numero]['documento'] = texto
            sesiones[numero]['paso'] = 'telefono'
            enviar_texto(numero, "📞 Escribe tu *número de teléfono*:")

        elif paso == 'telefono':
            sesiones[numero]['telefono'] = texto
            sesiones[numero]['paso'] = 'fecha'
            mostrar_fechas_disponibles(numero)

    # ── FLUJO CANCELAR ──
    elif flujo == 'cancelar':
        if paso == 'documento':
            buscar_y_cancelar_cita(numero, texto)

def mostrar_fechas_disponibles(numero):
    dias = obtener_proximos_dias_habiles()
    enviar_texto(numero, "📆 Selecciona una de las siguientes fechas disponibles:")

    # WhatsApp solo permite 3 botones máximo — perfecto
    botones = []
    for i, dia in enumerate(dias):
        botones.append({
            "type": "reply",
            "reply": {
                "id": f"fecha_{dia.replace(' ', '_')}",
                "title": dia[:20]  # máximo 20 caracteres por botón
            }
        })

    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "Elige tu fecha:"},
            "action": {"buttons": botones}
        }
    }
    enviar_request(data)

def confirmar_cita(numero, fecha):
    sesion = sesiones.get(numero, {})
    nombre = sesion.get('nombre', '')
    documento = sesion.get('documento', '')
    telefono = sesion.get('telefono', '')

    # Guardar en base de datos
    nueva_cita = Cita(
        nombre=nombre,
        documento=documento,
        telefono=telefono,
        fecha_cita=fecha,
        numero_whatsapp=numero,
        estado='activa'
    )
    db.session.add(nueva_cita)
    db.session.commit()

    agregar_mensajes_log(f"Cita agendada: {nombre} | {documento} | {fecha}")

    enviar_texto(numero,
        f"✅ *¡Cita agendada exitosamente!*\n\n"
        f"📋 *Resumen:*\n"
        f"• Nombre: {nombre}\n"
        f"• Documento: {documento}\n"
        f"• Teléfono: {telefono}\n"
        f"• Fecha: {fecha}\n\n"
        f"Te esperamos 😊"
    )

    del sesiones[numero]
    enviar_menu(numero)

# ─────────────────────────────────────────────
# CANCELAR CITA
# ─────────────────────────────────────────────

def buscar_y_cancelar_cita(numero, documento):
    cita = Cita.query.filter_by(documento=documento, estado='activa').first()

    if cita:
        sesiones[numero] = {
            'flujo': 'cancelar',
            'paso': 'confirmar',
            'cita_id': cita.id
        }

        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": f"Encontré tu cita:\n\n"
                            f"👤 {cita.nombre}\n"
                            f"📅 {cita.fecha_cita}\n\n"
                            f"¿Deseas cancelarla?"
                },
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "si_cancelar", "title": "✅ Sí, cancelar"}},
                        {"type": "reply", "reply": {"id": "no_cancelar", "title": "❌ No, mantener"}}
                    ]
                }
            }
        }
        enviar_request(data)
    else:
        enviar_texto(numero, "⚠️ No encontré ninguna cita activa con ese documento.")
        del sesiones[numero]
        enviar_menu(numero)

def ejecutar_cancelacion(numero):
    sesion = sesiones.get(numero, {})
    cita_id = sesion.get('cita_id')

    cita = Cita.query.get(cita_id)
    if cita:
        cita.estado = 'cancelada'
        db.session.commit()
        agregar_mensajes_log(f"Cita cancelada: {cita.nombre} | {cita.fecha_cita}")
        enviar_texto(numero, f"✅ Tu cita del *{cita.fecha_cita}* ha sido cancelada correctamente.")
    else:
        enviar_texto(numero, "⚠️ No se pudo cancelar la cita.")

    del sesiones[numero]
    enviar_menu(numero)

# ─────────────────────────────────────────────
# ENVÍO DE MENSAJES
# ─────────────────────────────────────────────

def enviar_menu(numero):
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "👋 ¿En qué podemos ayudarte?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "agendar",  "title": "📅 Agendar Cita"}},
                    {"type": "reply", "reply": {"id": "cancelar", "title": "❌ Cancelar Cita"}},
                    {"type": "reply", "reply": {"id": "asesoria", "title": "💬 Asesoría"}}
                ]
            }
        }
    }
    enviar_request(data)

def enviar_texto(numero, mensaje):
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "text",
        "text": {"preview_url": False, "body": mensaje}
    }
    enviar_request(data)

def enviar_request(data):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'bearer EAAY5YGNZBIz8BRAjKyKpEXAuVOPyfYNitaGXr1Ae5bSnu5LZBXDhUQ9pjUR81KSO4OJ5Imk5yOPURdMJzdCb961WrcpdHqDjbMrOEtORhU28bU03q8JfRfD1MKkQvZB26iVh2ey604MPpaaEfMJJLZCRZBdwVGLLFfO7pcHBm0cVisfJI1oZB5wbdFwAqqvoaxJNVAT46WdLrbX2dVgVdqHZBByd24HwNXpTqr02YbjaCkjs1twOl7AZBhjVZBjLrLuyvVOM3417FTDiZCZC6vMt144' 
    }
    connection = http.client.HTTPSConnection('graph.facebook.com')
    try:
        connection.request('POST', f'/v25.0/{PHONE_NUMBER_ID}/messages', json.dumps(data), headers)
        response = connection.getresponse()
        agregar_mensajes_log(f"Meta: {response.status} {response.reason}")
    except Exception as e:
        agregar_mensajes_log(f"Error envío: {str(e)}")
    finally:
        connection.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)