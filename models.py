from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

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
    fecha_cita = db.Column(db.String(50))
    numero_whatsapp = db.Column(db.String(20))
    estado = db.Column(db.String(20), default='activa')
    creada_en = db.Column(db.DateTime, default=datetime.utcnow)


class Consentimiento(db.Model):
    __tablename__ = 'consentimientos'

    id = db.Column(db.Integer, primary_key=True)
    numero_whatsapp = db.Column(db.String(20))
    acepto = db.Column(db.Boolean)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

def agregar_mensajes_log(texto):
    nuevo_registro = Log(texto=str(texto))
    db.session.add(nuevo_registro)
    db.session.commit()    