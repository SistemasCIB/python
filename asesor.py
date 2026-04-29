from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from models import db, Cita, Asesor, Auditoria, ChatActivo
from datetime import datetime, timedelta
from mensajes import enviar_texto
from config import HORARIO_INICIO, HORARIO_FIN
import io, csv, os
from flask import Response
from werkzeug.utils import secure_filename

asesor_bp = Blueprint('asesor', __name__)

def login_requerido(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('asesor_id'):
            return redirect(url_for('asesor.login'))
        return f(*args, **kwargs)
    return decorated

@asesor_bp.route('/asesor/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        password = request.form.get('password')
        asesor = Asesor.query.filter_by(usuario=usuario).first()
        if asesor and asesor.check_password(password):
            session['asesor_id'] = asesor.id
            session['asesor_nombre'] = asesor.nombre
            return redirect(url_for('asesor.panel'))
        error = "Usuario o contrasena incorrectos"
    return render_template('login.html', error=error)

@asesor_bp.route('/asesor/logout')
def logout():
    session.clear()
    return redirect(url_for('asesor.login'))

@asesor_bp.route('/asesor')
@login_requerido
def panel():
    citas = Cita.query.order_by(Cita.creada_en.desc()).all()
    return render_template('asesor.html',
        citas=citas,
        asesor_nombre=session.get('asesor_nombre'),
        horario_inicio=HORARIO_INICIO,
        horario_fin=HORARIO_FIN
    )

@asesor_bp.route('/asesor/confirmar/<int:cita_id>')
@login_requerido
def confirmar_cita(cita_id):
    cita = Cita.query.get(cita_id)
    if cita:
        cita.estado = 'confirmada'
        db.session.commit()
        log = Auditoria(
            asesor_id=session['asesor_id'],
            asesor_nombre=session['asesor_nombre'],
            accion='confirmo',
            cita_id=cita.id,
            detalle=f'Confirmó cita de {cita.nombre}'
        )
        db.session.add(log)
        db.session.commit()

        enviar_texto(cita.numero_whatsapp,
            f"Tu cita ha sido CONFIRMADA!\n\n"
            f"Tipo: {cita.tipo_cita.capitalize()}\n"
            f"Fecha: {cita.fecha_cita}\n"
            f"Hora: {cita.hora_cita}\n"
            f"Orden Médica: {cita.orden_medica}\n\n"
            f"Te esperamos. Horario: {HORARIO_INICIO}am a {HORARIO_FIN}pm."
        )
    return redirect(url_for('asesor.panel'))

@asesor_bp.route('/asesor/rechazar/<int:cita_id>')
@login_requerido
def rechazar_cita(cita_id):
    cita = Cita.query.get(cita_id)
    if cita:
        cita.estado = 'rechazada'
        db.session.commit()
        log = Auditoria(
            asesor_id=session['asesor_id'],
            asesor_nombre=session['asesor_nombre'],
            accion='rechazo',
            cita_id=cita.id,
            detalle=f'Rechazó cita de {cita.nombre}'
        )
        db.session.add(log)                                 
        db.session.commit()

        enviar_texto(cita.numero_whatsapp,
            f"Lo sentimos, tu solicitud de cita no pudo ser confirmada.\n\n"
            f"Para mas informacion contacta a nuestros asesores."
        )
    return redirect(url_for('asesor.panel'))

@asesor_bp.route('/asesor/exportar')
@login_requerido
def exportar_excel():
    citas = Cita.query.order_by(Cita.creada_en.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID','Nombre','Documento','Telefono','Tipo','Orden Médica','Fecha','Hora','WhatsApp','Estado','Registrada'])
    for c in citas:
        writer.writerow([c.id, c.nombre, c.documento, c.telefono,
                        c.tipo_cita, c.orden_medica, c.fecha_cita,
                        c.hora_cita, c.numero_whatsapp, c.estado,
                        c.creada_en.strftime('%d/%m/%Y %H:%M')])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=citas_cib.csv"}
    )



@asesor_bp.route('/asesor/nueva', methods=['GET', 'POST'])
@login_requerido
def nueva_cita():

    if request.method == 'POST':

        archivo = request.files.get('orden_medica')
        nombre_archivo = ''

        if archivo and archivo.filename != '':
            nombre_archivo = secure_filename(archivo.filename)
            ruta = os.path.join('static/uploads', nombre_archivo)
            archivo.save(ruta)

        # CORREGIR FECHA
        fecha_cita = datetime.strptime(
            request.form['fecha_cita'],
            '%Y-%m-%d'
        )

        cita = Cita(
            nombre=request.form['nombre'],
            tipo_documento=request.form['tipo_documento'],
            documento=request.form['documento'],
            telefono=request.form['telefono'],
            tipo_cita=request.form['tipo_cita'],
            orden_medica=nombre_archivo,
            fecha_cita=fecha_cita,
            hora_cita=request.form['hora_cita'],
            numero_whatsapp=request.form['telefono'],
            estado=request.form['estado']
        )

        db.session.add(cita)
        db.session.commit()

        log = Auditoria(
            asesor_id=session['asesor_id'],
            asesor_nombre=session['asesor_nombre'],
            accion='creo_manual',
            cita_id=cita.id,
            detalle=f'Creó cita manual para {cita.nombre}'
        )

        db.session.add(log)
        db.session.commit()

        return redirect(url_for('asesor.panel'))

    return render_template('form_cita.html', cita=None)


@asesor_bp.route('/asesor/editar/<int:cita_id>', methods=['GET', 'POST'])
@login_requerido
def editar_cita(cita_id):

    cita = Cita.query.get_or_404(cita_id)

    if request.method == 'POST':

        cita.nombre = request.form['nombre']
        cita.tipo_documento = request.form['tipo_documento']
        cita.documento = request.form['documento']
        cita.telefono = request.form['telefono']
        cita.tipo_cita = request.form['tipo_cita']

        # CORREGIR FECHA
        cita.fecha_cita = datetime.strptime(
            request.form['fecha_cita'],
            '%Y-%m-%d'
        )

        cita.hora_cita = request.form['hora_cita']
        cita.estado = request.form['estado']

        archivo = request.files.get('orden_medica')

        if archivo and archivo.filename != '':
            nombre_archivo = secure_filename(archivo.filename)
            ruta = os.path.join('static/uploads', nombre_archivo)
            archivo.save(ruta)

            cita.orden_medica = nombre_archivo

        db.session.commit()


        log = Auditoria(
            asesor_id=session['asesor_id'],
            asesor_nombre=session['asesor_nombre'],
            accion='editó',
            cita_id=cita.id,
            detalle=f'Editó cita de {cita.nombre}'
        )

        db.session.add(log)
        db.session.commit()

        return redirect(url_for('asesor.panel'))

    return render_template('form_cita.html', cita=cita)

@asesor_bp.route('/asesor/historial')
@login_requerido
def historial():

    logs = Auditoria.query.order_by(Auditoria.fecha.desc()).all()

    return render_template(
        'historial.html',
        logs=logs,
        asesor_nombre=session.get('asesor_nombre')
    )

@asesor_bp.route('/asesor/tomar_chat/<int:cita_id>')
@login_requerido
def tomar_chat(cita_id):

    cita = Cita.query.get_or_404(cita_id)

    chat = ChatActivo.query.filter_by(numero=cita.numero_whatsapp).first()

    if not chat:
        chat = ChatActivo(
            numero=cita.numero_whatsapp,
            asesor_id=session['asesor_id'],
            asesor_nombre=session['asesor_nombre'],
            activo=True,
            vence_en=datetime.utcnow() + timedelta(hours=24)
        )
        db.session.add(chat)
    else:
        chat.activo = True
        chat.asesor_id = session['asesor_id']
        chat.asesor_nombre = session['asesor_nombre']
        chat.vence_en = datetime.utcnow() + timedelta(hours=24)

    db.session.commit()

    return redirect(url_for('asesor.panel'))

@asesor_bp.route('/asesor/liberar_chat/<int:cita_id>')
@login_requerido
def liberar_chat(cita_id):

    cita = Cita.query.get_or_404(cita_id)

    chat = ChatActivo.query.filter_by(numero=cita.numero_whatsapp).first()

    if chat:
        db.session.delete(chat)
        db.session.commit()

    return redirect(url_for('asesor.panel'))

