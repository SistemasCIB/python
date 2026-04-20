from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

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
    estado = db.Column(db.String(20), default='activa')
    creada_en = db.Column(db.DateTime, default=datetime.utcnow)

class Consentimiento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_whatsapp = db.Column(db.String(20))
    acepto = db.Column(db.Boolean)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)