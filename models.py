from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha_y_hora = db.Column(db.DateTime, default=datetime.utcnow)
    texto = db.Column(db.TEXT)
def ordenar_por_fecha_y_hora(registros):
    return sorted(registros, key=lambda x: x.fecha_y_hora,reverse=True)

class Cita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    documento = db.Column(db.String(50))
    telefono = db.Column(db.String(20))
    tipo_cita = db.Column(db.String(20))        # presencial / domicilio
    motivo = db.Column(db.TEXT)
    fecha_cita = db.Column(db.String(50))
    numero_whatsapp = db.Column(db.String(20))
    estado = db.Column(db.String(20), default='pendiente')  # pendiente / confirmada / rechazada / cancelada
    creada_en = db.Column(db.DateTime, default=datetime.utcnow)


class Consentimiento(db.Model):
    __tablename__ = 'consentimientos'

    id = db.Column(db.Integer, primary_key=True)
    numero_whatsapp = db.Column(db.String(20))
    acepto = db.Column(db.Boolean)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class Asesor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(200))
    nombre = db.Column(db.String(100))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)    

def agregar_mensajes_log(texto):
    try:
        nuevo_registro = Log(texto=str(texto))
        db.session.add(nuevo_registro)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error log: {str(e)}")