from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
import json


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    city = db.Column(db.String(50), nullable=True)
    complaint_category = db.Column(db.String(100), nullable=True)
    incident_date = db.Column(db.String(50), nullable=True)
    delay_in_reporting = db.Column(db.String(10), nullable=True)
    platform = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=False)
    evidence_file = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(50), default='submitted')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # -------- Forensic Fields --------
    forensic_summary = db.Column(db.Text, nullable=True)   # dashboard-level summary (short JSON as string)
    forensic_details = db.Column(db.Text, nullable=True)

    # JSON helpers for SQLite
    def set_json_field(self, field_name, data):
        setattr(self, field_name, json.dumps(data))

    def get_json_field(self, field_name):
        val = getattr(self, field_name)
        return json.loads(val) if val else None

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "address": self.address,
            "email": self.email,
            "phone": self.phone,
            "state": self.state,
            "city": self.city,
            "complaint_category": self.complaint_category,
            "incident_date": self.incident_date,
            "delay_in_reporting": self.delay_in_reporting,
            "platform": self.platform,
            "description": self.description,
            "evidence_file": self.evidence_file,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "user_id": self.user_id,
            "forensic_summary": self.get_json_field("forensic_summary"),
            "forensic_details": self.get_json_field("forensic_details")
        }


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False) 
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reports = db.relationship('Report', backref='user', lazy=True)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)