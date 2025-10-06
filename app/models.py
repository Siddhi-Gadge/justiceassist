from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import json
from datetime import datetime
import json
from flask_sqlalchemy import SQLAlchemy


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    incident_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date_of_incident = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    evidence_text = db.Column(db.Text)
    status = db.Column(db.String(50), default='submitted')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # -------- Forensic Fields --------
    suspect_guess = db.Column(db.String(100), nullable=True)
    clues = db.Column(db.Text, nullable=True)         # JSON stored as string
    artifacts = db.Column(db.Text, nullable=True)     # JSON stored as string
    file_metadata = db.Column(db.Text, nullable=True) # JSON stored as string
    forensic_summary = db.Column(db.Text)   # dashboard-level summary (short JSON as string)
    forensic_details = db.Column(db.Text) 

    # JSON helpers for SQLite
    def set_json_field(self, field_name, data):
        setattr(self, field_name, json.dumps(data))

    def get_json_field(self, field_name):
        val = getattr(self, field_name)
        return json.loads(val) if val else None

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "incident_type": self.incident_type,
            "description": self.description,
            "date_of_incident": self.date_of_incident,
            "location": self.location,
            "evidence_text": self.evidence_text,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "user_id": self.user_id,
            "suspect_guess": self.suspect_guess,
            "clues": self.get_json_field("clues"),
            "artifacts": self.get_json_field("artifacts"),
            "file_metadata": self.get_json_field("file_metadata"),
            "forensic_summary": json.loads(self.forensic_summary) if self.forensic_summary else None,
            "forensic_details": json.loads(self.forensic_details) if self.forensic_details else None
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