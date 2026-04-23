from models import db, Cita, Consentimiento, agregar_mensajes_log
from mensajes import (enviar_texto, enviar_menu, enviar_bienvenida,
                      mostrar_fechas_disponibles, enviar_tipo_cita,
                      enviar_requisitos, enviar_fuera_horario, enviar_politica_datos)
from config import LINK_ASESOR, HORARIO_INICIO, HORARIO_FIN


sesiones = {}


def dentro_de_horario():
    from datetime import datetime, timedelta

    # Colombia UTC-5
    ahora = datetime.utcnow() - timedelta(hours=5)

    agregar_mensajes_log(
        f"Hora: {ahora.hour} | Min: {ahora.minute} | Dia: {ahora.weekday()}"
    )

    # 0 = lunes, 6 = domingo
    if ahora.weekday() >= 5:
        return False

    return 7 <= ahora.hour < 17

def manejar_boton(numero, opcion_id):

    sesion = sesiones.get(numero, {})
    if sesion.get('modo') == 'humano':
        return

    # ── Paciente o Cliente ──
    if opcion_id == 'soy_paciente':
        enviar_politica_datos(numero)
        return
    elif opcion_id == 'soy_cliente':
        enviar_texto(
            numero,
            f"Para atención comercial comunícate al siguiente LINK:\n\n{LINK_ASESOR}"
            )

    # ── POLÍTICA DE DATOS ──
    if opcion_id == 'acepto_datos':
        try:
            consentimiento = Consentimiento(numero_whatsapp=numero, acepto=True)
            db.session.add(consentimiento)
            db.session.commit()
            agregar_mensajes_log(f"Consentimiento ACEPTADO: {numero}")
            enviar_texto(numero, "Gracias por aceptar. Ahora puedes acceder a nuestros servicios.")
            enviar_menu(numero)
        except Exception as e:
            db.session.rollback()
            agregar_mensajes_log(f"Error consentimiento: {str(e)}")

    elif opcion_id == 'no_acepto_datos':
        try:
            consentimiento = Consentimiento(numero_whatsapp=numero, acepto=False)
            db.session.add(consentimiento)
            db.session.commit()
            agregar_mensajes_log(f"Consentimiento RECHAZADO: {numero}")
            enviar_texto(numero,
                "Has rechazado la politica de datos.\n\n"
                "Si cambias de opinion, escribe cualquier mensaje para comenzar de nuevo."
            )
        except Exception as e:
            db.session.rollback()
            agregar_mensajes_log(f"Error consentimiento: {str(e)}")

    # ── MENÚ PRINCIPAL ──
    elif opcion_id == 'agendar':
       if not dentro_de_horario():
          enviar_fuera_horario(numero)
          return
       sesiones[numero] = {'flujo': 'agendar', 'paso': 'tipo_cita'}
       enviar_tipo_cita(numero)

    elif opcion_id == 'cancelar':
        sesiones[numero] = {'flujo': 'cancelar', 'paso': 'documento'}
        enviar_texto(numero, "Cancelar Cita\n\nEscribe tu numero de documento para buscar tu cita:")

    elif opcion_id == 'asesoria':
        if not dentro_de_horario():
            enviar_fuera_horario(numero)
            return
        enviar_texto(numero,
            f"Estimados clientes\n\n"
            f"Les informamos que a partir de la fecha, todas las comunicaciones o solicitudes relacionadas con:\n"
            f"• Estado de resultados\n"
            f"• Dudas de remisiones\n"
            f"• Inquietudes sobre tipos y/o requisitos de muestras\n"
            f"• Información sobre días y horarios de procedimientos de laboratorio\n"
            f"• Entre otros temas similares\n\n"
            f"Deberán realizarse exclusivamente a través de nuestra línea de WhatsApp: \n"
            f"{LINK_ASESOR}\n\n"
            f"Agradecemos su comprensión y colaboración para centralizar la atención y brindarles un mejor servicio.\n\n"
            f"Les informamos que el horario oficial para la asignación de citas es de lunes a viernes {HORARIO_INICIO}am a {HORARIO_FIN}pm.\n"
            f"Las solicitudes realizadas fuera de este horario no podrán ser gestionadas. Por ello, agradecemos que las peticiones se envíen dentro del horario establecido para garantizar una atención oportuna y eficiente."

        )
        enviar_menu(numero)

    elif opcion_id == 'terminar':
        if numero in sesiones:
            del sesiones[numero]
        enviar_texto(numero, "Gracias por contactarnos. Hasta pronto!")

    # ── TIPO DE CITA ──
    elif opcion_id == 'tipo_presencial':
        sesiones[numero] = {'flujo': 'agendar', 'paso': 'requisitos', 'tipo_cita': 'presencial'}
        enviar_requisitos(numero, 'presencial')

    elif opcion_id == 'tipo_domicilio':
        sesiones[numero] = {'flujo': 'agendar', 'paso': 'requisitos', 'tipo_cita': 'domicilio'}
        enviar_requisitos(numero, 'domicilio')

    # ── REQUISITOS ──
    elif opcion_id == 'cumple_si':
        sesion = sesiones.get(numero, {})
        sesiones[numero]['paso'] = 'nombre'
        enviar_texto(numero, "Perfecto! Por favor escribe tu nombre completo:")

    elif opcion_id == 'cumple_no':
        if numero in sesiones:
            del sesiones[numero]
        enviar_texto(numero,
            "podras reangendar tu cita cuando cumplas con los requisitos necesarios.\n\n"
            
            
        )
        enviar_menu(numero)

    # ── SELECCIÓN DE FECHA ──
    elif opcion_id.startswith('fecha_'):
        sesion = sesiones.get(numero, {})
        fechas = sesion.get('fechas', {})
        fecha_elegida = fechas.get(opcion_id, opcion_id)
        sesiones[numero]['paso'] = 'motivo'
        sesiones[numero]['fecha_cita'] = fecha_elegida
        enviar_texto(numero, "Cual es el motivo de tu cita?")

    # ── CONFIRMAR CANCELACIÓN ──
    elif opcion_id == 'si_cancelar':
        ejecutar_cancelacion(numero)

    elif opcion_id == 'no_cancelar':
        if numero in sesiones:
            del sesiones[numero]
        enviar_texto(numero, "Tu cita no fue cancelada.")
        enviar_menu(numero)


def manejar_texto(numero, texto):
    from models import ChatActivo
    from datetime import datetime
    chat = ChatActivo.query.filter_by(
        numero=numero,
        activo=True
    ).first()

    if chat:
        if chat.vence_en > datetime.utcnow():
            return
        else:
            # venció el tiempo, liberar chat
            db.session.delete(chat)
            db.session.commit()

    # si esta en modo humano, el bot no responde
    sesion = sesiones.get(numero, {})
    if sesion.get('modo') == 'humano':
        return
        
    if numero not in sesiones:
        consentimiento = Consentimiento.query.filter_by(
            numero_whatsapp=numero, acepto=True
        ).first()
        if consentimiento:
            enviar_menu(numero)
        else:
            enviar_bienvenida(numero)
        return

    sesion = sesiones[numero]
    flujo = sesion.get('flujo')
    paso = sesion.get('paso')

    # ── FLUJO AGENDAR ──
    if flujo == 'agendar':
        if paso == 'nombre':
            sesiones[numero]['nombre'] = texto
            sesiones[numero]['paso'] = 'documento'
            enviar_texto(numero, "Escribe tu numero de documento de identidad:")

        elif paso == 'documento':
            sesiones[numero]['documento'] = texto
            sesiones[numero]['paso'] = 'telefono'
            enviar_texto(numero, "Escribe tu numero de telefono:")

        elif paso == 'telefono':
            sesiones[numero]['telefono'] = texto
            sesiones[numero]['paso'] = 'fecha'
            mostrar_fechas_disponibles(numero, sesiones)

        elif paso == 'motivo':
            sesiones[numero]['motivo'] = texto
            confirmar_cita(numero)

    # ── FLUJO CANCELAR ──
    elif flujo == 'cancelar':
        if paso == 'documento':
            buscar_y_cancelar_cita(numero, texto)


def confirmar_cita(numero):
    sesion = sesiones.get(numero, {})
    try:
        nueva_cita = Cita(
            nombre=sesion.get('nombre', ''),
            documento=sesion.get('documento', ''),
            telefono=sesion.get('telefono', ''),
            tipo_cita=sesion.get('tipo_cita', ''),
            motivo=sesion.get('motivo', ''),
            fecha_cita=sesion.get('fecha_cita', ''),
            numero_whatsapp=numero,
            estado='pendiente'
        )
        db.session.add(nueva_cita)
        db.session.commit()
        agregar_mensajes_log(f"Cita pendiente: {nueva_cita.nombre} | {nueva_cita.fecha_cita}")
        enviar_texto(numero,
            f"Tu solicitud de cita ha sido enviada!\n\n"
            f"Tipo: {nueva_cita.tipo_cita.capitalize()}\n"
            f"Fecha solicitada: {nueva_cita.fecha_cita}\n"
            f"Motivo: {nueva_cita.motivo}\n\n"
            f"Un asesor revisara tu solicitud y te confirmara pronto.\n"
            f"Horario de atencion: Lunes a viernes de {HORARIO_INICIO}am a {HORARIO_FIN}pm."
        )
    except Exception as e:
        db.session.rollback()
        agregar_mensajes_log(f"Error cita: {str(e)}")
    finally:
        sesiones[numero] = sesiones.get(numero, {})
        sesiones[numero]['modo'] = 'humano'
        


def buscar_y_cancelar_cita(numero, documento):
    cita = Cita.query.filter_by(documento=documento, estado='pendiente').first()
    if not cita:
        cita = Cita.query.filter_by(documento=documento, estado='confirmada').first()
    if cita:
        sesiones[numero] = {'flujo': 'cancelar', 'paso': 'confirmar', 'cita_id': cita.id}
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": f"Encontre tu cita:\n\nNombre: {cita.nombre}\nTipo: {cita.tipo_cita}\nFecha: {cita.fecha_cita}\n\nDeseas cancelarla?"},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "si_cancelar", "title": "Si, cancelar"}},
                        {"type": "reply", "reply": {"id": "no_cancelar", "title": "No, mantener"}}
                    ]
                }
            }
        }
        from mensajes import enviar_request
        enviar_request(data)
    else:
        enviar_texto(numero, "No encontre ninguna cita activa con ese documento.")
        if numero in sesiones:
            del sesiones[numero]
        enviar_menu(numero)


def ejecutar_cancelacion(numero):
    sesion = sesiones.get(numero, {})
    cita = Cita.query.get(sesion.get('cita_id'))
    try:
        if cita:
            cita.estado = 'cancelada'
            db.session.commit()
            agregar_mensajes_log(f"Cita cancelada: {cita.nombre} | {cita.fecha_cita}")
            enviar_texto(numero, f"Tu cita del {cita.fecha_cita} ha sido cancelada.")
        else:
            enviar_texto(numero, "No se pudo cancelar la cita.")
    except Exception as e:
        db.session.rollback()
        agregar_mensajes_log(f"Error cancelacion: {str(e)}")
    finally:
        if numero in sesiones:
            del sesiones[numero]
        enviar_menu(numero)