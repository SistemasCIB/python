from models import db, Cita, Consentimiento, agregar_mensajes_log
from mensajes import (enviar_texto, enviar_menu, enviar_bienvenida, enviar_tipo_documento,
                      mostrar_fechas_disponibles, enviar_tipo_cita,
                      enviar_requisitos, enviar_fuera_horario, enviar_politica_datos
                      )
from config import LINK_ASESOR, HORARIO_INICIO, HORARIO_FIN, URL_RESULTADOS
from datetime import datetime, timedelta


sesiones = {}

MODO_HUMANO_MINUTOS = 3


def dentro_de_horario():
    # Colombia UTC-5
    ahora = datetime.utcnow() - timedelta(hours=5)

    agregar_mensajes_log(
        f"Hora: {ahora.hour} | Min: {ahora.minute} | Dia: {ahora.weekday()}"
    )

    # 0 = lunes, 6 = domingo
    if ahora.weekday() >= 5:
        return False

    return 7 <= ahora.hour < 17


def verificar_modo_humano(numero):
    """
    Retorna True si el número sigue en modo humano activo.
    Si ya venció el tiempo, limpia el modo y retorna False.
    """
    sesion = sesiones.get(numero, {})
    if sesion.get('modo') != 'humano':
        return False

    inicio = sesion.get('modo_humano_inicio')
    if inicio is None:
        # No tiene timestamp, se lo asignamos ahora por compatibilidad
        sesiones[numero]['modo_humano_inicio'] = datetime.utcnow()
        return True

    tiempo_transcurrido = datetime.utcnow() - inicio
    if tiempo_transcurrido >= timedelta(minutes=MODO_HUMANO_MINUTOS):
        # Venció: limpiar modo humano
        agregar_mensajes_log(f"Modo humano vencido para {numero}, liberando sesión.")
        del sesiones[numero]
        return False

    return True


def manejar_boton(numero, opcion_id):

    if verificar_modo_humano(numero):
        return

    # ── Paciente o Cliente ──
    if opcion_id == 'soy_paciente':
        enviar_politica_datos(numero)
        return
    elif opcion_id == 'soy_cliente':
        enviar_texto(
            numero,
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
                "👋 Gracias por contactarnos.\n\n"
                "Para poder atender tu solicitud es necesario aceptar nuestra política de tratamiento de datos.\n\n"
                "Si en otro momento decides continuar, estaremos atentos para ayudarte.\n\n"
                "¡Que tengas un excelente día!💙"
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

    elif opcion_id == "resultados":
        enviar_texto(
            numero,
            f"Consulta de resultados:\n\n"
            f"1. Ingresa al enlace:\n{URL_RESULTADOS}\n\n"
            f"2. Selecciona RESULTADOS LABCORE.\n"
            f"3. Usuario: número de documento.\n"
            f"4. Contraseña: últimos 4 dígitos del documento.\n"
            f"5. Descarga el resultado.\n\n"
            f"Gracias por confiar en nosotros."
        )
        enviar_menu(numero)

    elif opcion_id == "otros":
        enviar_texto(
            numero,
            "Otros servicios:\n\n"
            "Fondo editorial CIB\n"
            "3042151025\n"
            "gestorcomercial@cib.org.co\n\n"
            "Programa ALIMENTATEC\n"
            "3235865867\n"
            "alimentatec@cib.org.co\n\n"
            "Generalidades\n"
            "comunicacionesymercadeo@cib.org.co\n\n"
            "Gracias por confiar en nosotros."
        )
        enviar_menu(numero)

    elif opcion_id == "terminar":
        if numero in sesiones:
            del sesiones[numero]
        enviar_texto(numero, "Gracias por contactarnos. Hasta pronto.")

    # ── TIPO DE CITA ──
    elif opcion_id == 'tipo_presencial':
        sesiones[numero] = {'flujo': 'agendar', 'paso': 'requisitos', 'tipo_cita': 'presencial'}
        enviar_requisitos(numero, 'presencial')

    elif opcion_id == 'tipo_domicilio':
        sesiones[numero] = {'flujo': 'agendar', 'paso': 'requisitos', 'tipo_cita': 'domicilio'}
        enviar_requisitos(numero, 'domicilio')

    # ── REQUISITOS ──
    elif opcion_id == 'cumple_si':
        sesiones[numero]['paso'] = 'tipo_documento'
        enviar_tipo_documento(numero)

    elif opcion_id.startswith('tdoc_'):
        tipo_documento = opcion_id.split('_')[1]
        sesiones[numero]['tipo_documento'] = tipo_documento
        sesiones[numero]['paso'] = 'nombre'
        enviar_texto(numero, "Escribe tu numero de documento de identificacion:")

    elif opcion_id == 'cumple_no':
        if numero in sesiones:
            del sesiones[numero]
        enviar_texto(numero,
            "Podras reagendar tu cita cuando cumplas con los requisitos necesarios.\n\n"
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


def manejar_texto(numero, texto):
    from models import ChatActivo

    chat = ChatActivo.query.filter_by(
        numero=numero,
        activo=True
    ).first()

    if chat:
        if chat.vence_en > datetime.utcnow():
            return
        else:
            db.session.delete(chat)
            db.session.commit()

    if verificar_modo_humano(numero):
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
        if paso == 'documento':
            sesiones[numero]['documento'] = texto
            sesiones[numero]['paso'] = 'nombre'
            enviar_texto(numero, "Escribe tus nombres y apellidos completos (como aparecen en tu documento):")

        elif paso == 'nombre':
            sesiones[numero]['nombre'] = texto
            sesiones[numero]['paso'] = 'telefono'
            enviar_texto(numero, "Escribe tu numero de telefono:")

        elif paso == 'telefono':
            sesiones[numero]['telefono'] = texto
            sesiones[numero]['paso'] = 'correo'
            enviar_texto(numero, "Escribe tu correo electronico:")

        elif paso == 'correo':
            sesiones[numero]['correo'] = texto
            sesiones[numero]['paso'] = 'direccion'
            enviar_texto(numero, "Escribe tu direccion completa:")

        elif paso == 'direccion':
            sesiones[numero]['direccion'] = texto
            sesiones[numero]['paso'] = 'motivo'
            enviar_texto(numero, "Escribe el motivo de tu cita:")

        elif paso == 'motivo':
            sesiones[numero]['motivo'] = texto
            confirmar_cita(numero)


def confirmar_cita(numero):
    sesion = sesiones.get(numero, {})
    try:
        nueva_cita = Cita(
            tipo_documento=sesion.get('tipo_documento', ''),
            nombre=sesion.get('nombre', ''),
            documento=sesion.get('documento', ''),
            telefono=sesion.get('telefono', ''),
            correo=sesion.get('correo', ''),
            direccion=sesion.get('direccion', ''),
            tipo_cita=sesion.get('tipo_cita', ''),
            motivo=sesion.get('motivo', ''),
            fecha_cita=sesion.get('fecha_cita', ''),
            hora_cita=sesion.get('hora_cita', ''),
            numero_whatsapp=numero,
            estado='pendiente'
        )
        db.session.add(nueva_cita)
        db.session.commit()
        agregar_mensajes_log(f"Cita pendiente: {nueva_cita.nombre} | {nueva_cita.fecha_cita}")
        enviar_texto(numero,
            f"Tu solicitud de cita ha sido enviada!\n\n"
            f"Nombre: {nueva_cita.nombre}\n"
            f"Documento: {nueva_cita.tipo_documento} {nueva_cita.documento}\n"
            f"Telefono: {nueva_cita.telefono}\n"
            f"Correo: {nueva_cita.correo}\n"
            f"Direccion: {nueva_cita.direccion}\n"
            f"Tipo: {nueva_cita.tipo_cita.capitalize()}\n"
            f"Fecha solicitada: {nueva_cita.fecha_cita}\n"
            f"Hora solicitada: {nueva_cita.hora_cita}\n"
            f"Motivo: {nueva_cita.motivo}\n\n"
            f"Un asesor confirmara tu cita pronto."
        )
    except Exception as e:
        db.session.rollback()
        agregar_mensajes_log(f"Error cita: {str(e)}")
    finally:
        # Activar modo humano con timestamp
        sesiones[numero] = {
            'modo': 'humano',
            'modo_humano_inicio': datetime.utcnow()
        }