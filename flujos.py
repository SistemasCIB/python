from models import db, Cita, Consentimiento, agregar_mensajes_log
from mensajes import enviar_texto, enviar_menu, enviar_bienvenida, mostrar_fechas_disponibles
from config import LINK_ASESOR

sesiones = {}


def manejar_boton(numero, opcion_id):

    # ── POLÍTICA DE DATOS ──
    if opcion_id == 'acepto_datos':
        from models import db
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
        from models import db
        try:
            consentimiento = Consentimiento(numero_whatsapp=numero, acepto=False)
            db.session.add(consentimiento)
            db.session.commit()
            agregar_mensajes_log(f"Consentimiento RECHAZADO: {numero}")
            enviar_texto(numero,
                "Has rechazado la politica de datos.\n\n"
                "Lamentablemente no podemos continuar sin tu autorizacion. "
                "Si cambias de opinion, escribe cualquier mensaje para comenzar de nuevo."
            )
        except Exception as e:
            db.session.rollback()
            agregar_mensajes_log(f"Error consentimiento: {str(e)}")

    # ── MENÚ PRINCIPAL ──
    elif opcion_id == 'agendar':
        sesiones[numero] = {'flujo': 'agendar', 'paso': 'nombre'}
        enviar_texto(numero, "Agendar Cita\n\nPor favor escribe tu nombre completo:")

    elif opcion_id == 'cancelar':
        sesiones[numero] = {'flujo': 'cancelar', 'paso': 'documento'}
        enviar_texto(numero, "Cancelar Cita\n\nEscribe tu numero de documento para buscar tu cita:")

    elif opcion_id == 'asesoria':
        enviar_texto(numero,
            f"Asesoria\n\nHaz clic en el siguiente enlace para chatear directamente con uno de nuestros asesores:\n\n"
            f"Telefono: {LINK_ASESOR}\n\nEstara feliz de ayudarte!"
        )
        enviar_menu(numero)

    elif opcion_id == 'terminar':
        if numero in sesiones:
            del sesiones[numero]
        enviar_texto(numero, "Gracias por contactarnos. Hasta pronto!")

    # ── SELECCIÓN DE FECHA ──
    elif opcion_id.startswith('fecha_'):
        sesion = sesiones.get(numero, {})
        fechas = sesion.get('fechas', {})
        fecha_elegida = fechas.get(opcion_id, opcion_id)
        confirmar_cita(numero, fecha_elegida)

    # ── CONFIRMAR CANCELACIÓN ──
    elif opcion_id == 'si_cancelar':
        ejecutar_cancelacion(numero)

    elif opcion_id == 'no_cancelar':
        if numero in sesiones:
            del sesiones[numero]
        enviar_texto(numero, "Tu cita no fue cancelada.")
        enviar_menu(numero)


def manejar_texto(numero, texto):
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

    # ── FLUJO CANCELAR ──
    elif flujo == 'cancelar':
        if paso == 'documento':
            buscar_y_cancelar_cita(numero, texto)


def confirmar_cita(numero, fecha):
    from models import db
    sesion = sesiones.get(numero, {})
    try:
        nueva_cita = Cita(
            nombre=sesion.get('nombre', ''),
            documento=sesion.get('documento', ''),
            telefono=sesion.get('telefono', ''),
            fecha_cita=fecha,
            numero_whatsapp=numero,
            estado='activa'
        )
        db.session.add(nueva_cita)
        db.session.commit()
        agregar_mensajes_log(f"Cita agendada: {nueva_cita.nombre} | {fecha}")
        enviar_texto(numero,
            f"Cita agendada exitosamente!\n\n"
            f"Nombre: {nueva_cita.nombre}\n"
            f"Documento: {nueva_cita.documento}\n"
            f"Telefono: {nueva_cita.telefono}\n"
            f"Fecha: {fecha}\n\n"
            f"Te esperamos!"
        )
    except Exception as e:
        db.session.rollback()
        agregar_mensajes_log(f"Error cita: {str(e)}")
    finally:
        if numero in sesiones:
            del sesiones[numero]
        enviar_menu(numero)


def buscar_y_cancelar_cita(numero, documento):
    cita = Cita.query.filter_by(documento=documento, estado='activa').first()
    if cita:
        sesiones[numero] = {'flujo': 'cancelar', 'paso': 'confirmar', 'cita_id': cita.id}
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": f"Encontre tu cita:\n\nNombre: {cita.nombre}\nFecha: {cita.fecha_cita}\n\nDeseas cancelarla?"},
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
    from models import db
    sesion = sesiones.get(numero, {})
    cita = Cita.query.get(sesion.get('cita_id'))
    try:
        if cita:
            cita.estado = 'cancelada'
            db.session.commit()
            agregar_mensajes_log(f"Cita cancelada: {cita.nombre} | {cita.fecha_cita}")
            enviar_texto(numero, f"Tu cita del {cita.fecha_cita} ha sido cancelada correctamente.")
        else:
            enviar_texto(numero, "No se pudo cancelar la cita.")
    except Exception as e:
        db.session.rollback()
        agregar_mensajes_log(f"Error cancelacion: {str(e)}")
    finally:
        if numero in sesiones:
            del sesiones[numero]
        enviar_menu(numero)