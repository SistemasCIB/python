from models import db, Cita,Paciente, Consentimiento, agregar_mensajes_log
from mensajes import (
    enviar_texto,
    enviar_menu,
    enviar_bienvenida,
    enviar_tipo_documento,
    mostrar_fechas_disponibles,
    enviar_tipo_cita,
    enviar_requisitos,
    enviar_fuera_horario,
    enviar_politica_datos,
    enviar_tipo_cobertura,
    enviar_aseguradora,
    enviar_tipo_examen,
    mostrar_horas_disponibles
)

from config import LINK_ASESOR, HORARIO_INICIO, HORARIO_FIN, URL_RESULTADOS
from datetime import datetime, timedelta

sesiones = {}
MODO_HUMANO_MINUTOS = 3


# =====================================================
# HORARIO
# =====================================================

def dentro_de_horario():
    ahora = datetime.utcnow() - timedelta(hours=5)

    if ahora.weekday() >= 5:
        return False

    return 7 <= ahora.hour < 17


# =====================================================
# MODO HUMANO
# =====================================================

def verificar_modo_humano(numero):
    sesion = sesiones.get(numero, {})

    if sesion.get("modo") != "humano":
        return False

    inicio = sesion.get("modo_humano_inicio")

    if not inicio:
        sesiones[numero]["modo_humano_inicio"] = datetime.utcnow()
        return True

    if datetime.utcnow() - inicio >= timedelta(minutes=MODO_HUMANO_MINUTOS):
        del sesiones[numero]
        return False

    return True


# =====================================================
# BOTONES
# =====================================================

def manejar_boton(numero, opcion_id):

    if verificar_modo_humano(numero):
        return

    # -----------------------------------
    # PACIENTE / CLIENTE
    # -----------------------------------
    if opcion_id == "soy_paciente":
        enviar_politica_datos(numero)
        return

    elif opcion_id == "soy_cliente":
        enviar_texto(
            numero,
            f"Para clientes institucionales comunícate a:\n{LINK_ASESOR}"
        )
        return

    # -----------------------------------
    # POLITICA
    # -----------------------------------
    elif opcion_id == "acepto_datos":
        try:
            consentimiento = Consentimiento(
                numero_whatsapp=numero,
                acepto=True
            )
            db.session.add(consentimiento)
            db.session.commit()

        except:
            db.session.rollback()

        enviar_menu(numero)
        return

    elif opcion_id == "no_acepto_datos":
        enviar_texto(
            numero,
            "Para continuar debes aceptar la política de datos."
        )
        return

    # -----------------------------------
    # MENU
    # -----------------------------------
    elif opcion_id == "agendar":

        if not dentro_de_horario():
            enviar_fuera_horario(numero)
            return

        #primero busca si ya es un paciente existente
        sesiones[numero] = {
            "flujo": "agendar",
            "paso": "buscar_documento"
        }
        enviar_texto(
            numero,
            "📋 Para comenzar, escribe tu número de documento de identidad:"
        )    

        return

    elif opcion_id == "resultados":
        enviar_texto(
            numero,
            f"Ingreso resultados:\n{URL_RESULTADOS}"
        )
        return

    elif opcion_id == "otros":
        enviar_texto(numero, "Próximamente.")
        return

    elif opcion_id == "terminar":
        if numero in sesiones:
            del sesiones[numero]

        enviar_texto(numero, "Gracias por contactarnos.")
        return

    # -----------------------------------
    # PASO 1 - DATOS PACIENTE: tipo documento
    # -----------------------------------
    elif opcion_id.startswith("tdoc_"):

        sesiones[numero]["tipo_documento"] = opcion_id.replace("tdoc_", "")
        sesiones[numero]["paso"] = "documento"

        enviar_texto(
            numero,
            "Escribe tu número de documento:"
        )
        return

    # -----------------------------------
    # PASO 2 - COBERTURA: después de dirección
    # -----------------------------------
    elif opcion_id == "cobertura_particular":

        sesiones[numero]["cobertura"] = "Particular"
        sesiones[numero]["paso"] = "tipo_examen"

        enviar_tipo_examen(numero)
        return

    elif opcion_id == "cobertura_poliza":

        sesiones[numero]["cobertura"] = "Poliza"
        sesiones[numero]["paso"] = "aseguradora"

        enviar_aseguradora(numero)
        return

    # -----------------------------------
    # ASEGURADORA
    # -----------------------------------
    elif opcion_id.startswith("seg_"):

        sesiones[numero]["aseguradora"] = opcion_id
        sesiones[numero]["paso"] = "tipo_examen"

        enviar_tipo_examen(numero)
        return

    # -----------------------------------
    # PASO 3 - TIPO EXAMEN: después de cobertura
    # -----------------------------------
    elif opcion_id.startswith("examen_"):

        examenes = {
            "examen_directo_hongos": "Examen directo hongos",
            "examen_directo_cultivo": "Hongos + Cultivo",
            "examen_galactomanano": "Galactomanan",
            "examen_cryptococcus": "Cryptococcus",
            "examen_serologia_inmuno": "Serologia hongos",
            "examen_serologia_complemento": "Serologia endemicos",
            "examen_igra": "IGRAs",
            "examen_ppd": "Tuberculina"
        }

        if opcion_id == "examen_otro":
            sesiones[numero]["paso"] = "examen_otro_texto"

            enviar_texto(
                numero,
                "Escribe el nombre completo del examen:"
            )
            return

        sesiones[numero]["tipo_examen"] = examenes.get(opcion_id)
        # FLUJO: después de examen → requisitos
        sesiones[numero]["paso"] = "requisitos"

        enviar_requisitos(numero, "general")
        return

    # -----------------------------------
    # PASO 4 - REQUISITOS: después de examen
    # -----------------------------------
    elif opcion_id == "cumple_si":
        # FLUJO: después de requisitos → tipo_cita
        sesiones[numero]["paso"] = "tipo_cita"

        enviar_tipo_cita(numero)
        return
    elif opcion_id == "cumple_no":
        enviar_texto(
            numero,
            "Cuando cumplas requisitos podremos ayudarte."
        )
        enviar_menu(numero)
        return

    # -----------------------------------
    # PASO 5 - TIPO CITA: después de requisitos
    # -----------------------------------
    elif opcion_id == "tipo_presencial":

        sesiones[numero]["tipo_cita"] = "presencial"
        # FLUJO: después de tipo_cita → fecha
        sesiones[numero]["paso"] = "fecha"

        mostrar_fechas_disponibles(numero, sesiones)
        return

    elif opcion_id == "tipo_domicilio":

        sesiones[numero]["tipo_cita"] = "domicilio"
        # FLUJO: después de tipo_cita → fecha
        sesiones[numero]["paso"] = "fecha"

        mostrar_fechas_disponibles(numero, sesiones)
        return

    # -----------------------------------
    # PASO 6 - FECHA: después de tipo_cita
    # -----------------------------------
    elif opcion_id.startswith("fecha_"):

        fecha = sesiones[numero]["fechas"].get(opcion_id)

        sesiones[numero]["fecha_cita"] = fecha
        if sesiones[numero]["tipo_cita"] == "presencial":
            sesiones[numero]["paso"] = "hora"
            mostrar_horas_disponibles(numero, sesiones)
           
            return
        else:    
        ## Si es domicilio no pide hora
           sesiones[numero]["hora_cita"] = "Por asignar"
           sesiones[numero]["paso"] = "direccion_domicilio"

        enviar_texto(
            numero,
            "🏠 *Dirección para domicilio*\n\n"
            "Por favor envíanos la dirección completa para la toma de la muestra:\n\n"
            "• Dirección exacta\n"
            "• Barrio\n"
            "• Municipio\n"
            "• Punto de referencia (ej: cerca a…, edificio, apartamento, casa, local…)\n"
            "• Número de teléfono de contacto"
        )
        return
    # -----------------------------------
    # PASO 7 - HORA
    # -----------------------------------
    elif opcion_id.startswith("hora_"):

        hora = sesiones[numero]["horas"].get(opcion_id)

        sesiones[numero]["hora_cita"] = hora
        sesiones[numero]["paso"] = "orden"

        enviar_texto(
            numero,
            "📄 Ahora adjunta la orden médica.\n\n"
            "Puedes enviarla en PDF o foto.\n"
            "Un asesor la revisará para confirmar tu cita."
        )
        return

# =====================================================
# MENSAJES TEXTO
# =====================================================

def manejar_texto(numero, texto):

    if verificar_modo_humano(numero):
        return

    if numero not in sesiones:
        enviar_bienvenida(numero)
        return

    sesion = sesiones[numero]
    paso = sesion.get("paso")

    # -----------------------------------
    # BUSCAR PACIENTE POR DOCUMENTO
    # -----------------------------------
    if paso == "buscar_documento":
        from models import Paciente

        paciente = Paciente.query.filter_by(documento=texto.strip()).first()

        if paciente:
            # Paciente encontrado — cargar datos y saltar al flujo
            sesiones[numero]["tipo_documento"] = paciente.tipo_documento
            sesiones[numero]["documento"]      = paciente.documento
            sesiones[numero]["nombre"]         = paciente.nombre
            sesiones[numero]["telefono"]       = paciente.telefono
            sesiones[numero]["correo"]         = paciente.correo
            sesiones[numero]["direccion"]      = paciente.direccion
            sesiones[numero]["paso"]           = "cobertura"

            enviar_texto(
                numero,
                f"👤 Bienvenido de nuevo, *{paciente.nombre}*.\n"
                f"Usaremos tus datos registrados."
            )
            enviar_tipo_cobertura(numero)

        else:
            # Paciente nuevo — pedir datos completos
            sesiones[numero]["paso"] = "tipo_documento"
            enviar_tipo_documento(numero)

        return

    # -----------------------------------
    # EXAMEN OTRO
    # -----------------------------------
    if paso == "examen_otro_texto":
        sesiones[numero]["tipo_examen"] = texto
        # FLUJO: después de examen otro → requisitos
        sesiones[numero]["paso"] = "requisitos"

        enviar_requisitos(numero, "general")
        return

    # -----------------------------------
    # DATOS PACIENTE: número de documento
    # -----------------------------------
    elif paso == "documento":
        sesiones[numero]["documento"] = texto
        sesiones[numero]["paso"] = "nombre"

        enviar_texto(
            numero,
            "Escribe tus nombres y apellidos:"
        )
        return

    # -----------------------------------
    # DATOS PACIENTE: nombre
    # -----------------------------------
    elif paso == "nombre":
        sesiones[numero]["nombre"] = texto
        sesiones[numero]["paso"] = "telefono"

        enviar_texto(
            numero,
            "Escribe tu número de teléfono:"
        )
        return

    # -----------------------------------
    # DATOS PACIENTE: teléfono
    # -----------------------------------
    elif paso == "telefono":
        sesiones[numero]["telefono"] = texto
        sesiones[numero]["paso"] = "correo"

        enviar_texto(
            numero,
            "Escribe tu correo electrónico:"
        )
        return

    # -----------------------------------
    # DATOS PACIENTE: correo
    # -----------------------------------
    elif paso == "correo":
        sesiones[numero]["correo"] = texto
        sesiones[numero]["paso"] = "direccion"

        enviar_texto(
            numero,
            "Escribe tu dirección completa:"
        )
        return

    # -----------------------------------
    # DATOS PACIENTE: dirección
    # FLUJO: después de dirección → cobertura
    # -----------------------------------
    elif paso == "direccion":
        sesiones[numero]["direccion"] = texto
        sesiones[numero]["paso"] = "cobertura"

        enviar_tipo_cobertura(numero)
        return
    
    # -----------------------------------
    #DIRECION DOMICILIO
    # -----------------------------------
    elif paso == "direccion_domicilio":
        sesiones[numero]["direccion_domicilio"] = texto
        sesiones[numero]["paso"] = "orden"
        enviar_texto(
            numero,
            "📄 Ahora adjunta la orden médica.\n\n"
            "Puedes enviarla en PDF o foto.\n"
            "Un asesor la revisará para confirmar tu cita."
        )
        return




    # -----------------------------------
    # ORDEN (captura por texto — error)
    # -----------------------------------
    elif paso == "orden":
        enviar_texto(
            numero,
            "Por favor envía la orden como foto 📷 o archivo PDF 📄, no como texto."
        )
        return

    # -----------------------------------
    # POST CITA (re-agendar)
    # -----------------------------------
    elif paso == "post_cita":

        if texto == "1":
            # MISMO PACIENTE
            sesiones[numero]["paso"] = "cobertura"

            enviar_texto(
                numero,
                "Perfecto 👍 agendaremos otra cita con los mismos datos."
            )

            enviar_tipo_cobertura(numero)
            return

        elif texto == "2":
            # OTRO PACIENTE
            sesiones[numero] = {
                "flujo": "agendar",
                "paso": "buscar_documento"
            }

            enviar_texto(
                numero,
                "📋 Ingresa el documento del nuevo paciente:"
            )
            return

        elif texto == "3":
            # TERMINAR
            enviar_texto(
                numero,
                "Gracias por confiar en nosotros 💙"
            )

            sesiones[numero] = {
                "modo": "humano",
                "modo_humano_inicio": datetime.utcnow()
            }
            return

        else:
            enviar_texto(
                numero,
                "Por favor responde con:\n1, 2 o 3"
            )
            return

def manejar_archivo(numero, media_id, tipo_mime):
    if numero not in sesiones:
        return
    if sesiones[numero].get("paso") != "orden":
        return

    sesiones[numero]["orden"] = media_id
    sesiones[numero]["tipo_archivo"] = tipo_mime
    confirmar_cita(numero)




# =====================================================
# GUARDAR CITA
# =====================================================

def confirmar_cita(numero):
    sesion = sesiones.get(numero, {})

    try:
        from datetime import datetime

        # ---------------------------------
        # FECHA
        # ---------------------------------
        fecha_texto = sesion.get("fecha_cita", "").strip()
        hora_texto = sesion.get("hora_cita", "").strip()

        if hora_texto and hora_texto != "Por asignar":
            fecha_real = datetime.strptime(
                f"{fecha_texto} {hora_texto}",
                "%d/%m/%Y %H:%M"
            )
        else:
            fecha_real = datetime.strptime(
                fecha_texto,
                "%d/%m/%Y"
            )

        # ---------------------------------
        # PACIENTE — busca o crea
        # ---------------------------------
        paciente = Paciente.query.filter_by(
            documento=sesion.get("documento")
        ).first()

        if not paciente:
            paciente = Paciente(
                tipo_documento=sesion.get("tipo_documento", ""),
                documento=sesion.get("documento", ""),
                nombre=sesion.get("nombre", ""),
                telefono=sesion.get("telefono", ""),
                correo=sesion.get("correo", ""),
                direccion=sesion.get("direccion", ""),
                numero_whatsapp=numero
            )
            db.session.add(paciente)
            db.session.flush()  # obtiene paciente.id sin commit

        # ---------------------------------
        # CITA
        # ---------------------------------
        cita = Cita(
            paciente_id=paciente.id,
            tipo_cita=sesion.get("tipo_cita", ""),
            direccion_domicilio=sesion.get("direccion_domicilio", ""),
            orden_medica=sesion.get("orden", ""),
            orden_tipo_archivo=sesion.get("tipo_archivo", ""),
            cobertura=sesion.get("cobertura", ""),
            aseguradora=sesion.get("aseguradora", ""),
            tipo_examen=sesion.get("tipo_examen", ""),
            fecha_cita=fecha_real,
            hora_cita=hora_texto if hora_texto else "Por asignar",
            numero_whatsapp=numero,
            estado="pendiente"
        )

        db.session.add(cita)
        db.session.commit()

        enviar_texto(
            numero,
            "✅ Tu solicitud fue enviada correctamente.\n\n"
            "Un asesor validará la información y confirmará tu cita.\n\n"
            "¿Deseas agendar otra cita?\n\n"
            "1️⃣ Mismo paciente\n" 
            "2️⃣ Otro paciente\n"
            "3️⃣ No, gracias"
        )
        sesiones[numero]["paso"] = "post_cita"
        return

    except Exception as e:
        db.session.rollback()
        agregar_mensajes_log(str(e))

        enviar_texto(
            numero,
            "❌ Ocurrió un error guardando tu solicitud."
        )

    sesiones[numero] = {
        "modo": "humano",
        "modo_humano_inicio": datetime.utcnow()
    }