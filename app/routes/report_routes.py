from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Report
from app import db
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

report = Blueprint('report', __name__)

@report.route('/submit-report', methods=['POST'])
@jwt_required()
def submit_report():
    user_id = get_jwt_identity()
    data = request.get_json()

    title = data.get("title")
    description = data.get("description")
    evidence_text = data.get("evidence_text")  # 👈 use lowercase to match JSON key

    if not title or not description or not evidence_text:
        return jsonify({"error": "Title, description, and evidence_text are required"}), 400

    new_report = Report(
    title=title,
    incident_type=data.get("incident_type"),
    description=description,
    evidence_text=evidence_text,
    date_of_incident=data.get("date_of_incident"),
    location=data.get("location"),
    user_id=user_id,
    created_at=datetime.utcnow()
)

    db.session.add(new_report)
    db.session.commit()

    return jsonify({"message": "Report submitted successfully"}), 201

@report.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    current_user_id = get_jwt_identity()
    user_reports = Report.query.filter_by(user_id=current_user_id).order_by(Report.created_at.desc()).all()

    reports_data = [{
        "id": report.id,
        "title": report.title,
        "description": report.description,
        "evidence_text": report.evidence_text,
        "created_at": report.created_at.strftime("%Y-%m-%d %H:%M:%S")
    } for report in user_reports]

    return jsonify({"reports": reports_data}), 200

@report.route('/download/<int:report_id>', methods=['GET'])
@jwt_required()
def download_report(report_id):
    user_id = get_jwt_identity()
    report_obj = Report.query.filter_by(id=report_id, user_id=user_id).first()

    if not report_obj:
        return jsonify({"error": "Report not found"}), 404

    pdf_path = f"report_{report_id}.pdf"

    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, height - 50, "Cybercrime Report Summary")

    c.setFont("Helvetica", 12)
    c.drawString(100, height - 100, f"Report ID: {report_obj.id}")
    c.drawString(100, height - 120, f"Submitted on: {report_obj.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

    c.drawString(100, height - 160, f"Title: {report_obj.title}")
    c.drawString(100, height - 180, f"Description:")
    text_object = c.beginText(100, height - 200)
    for line in report_obj.description.split('\n'):
        text_object.textLine(line)
    c.drawText(text_object)

    c.drawString(100, text_object.getY() - 20, f"Evidence Text:")
    text_object2 = c.beginText(100, text_object.getY() - 40)
    for line in report_obj.evidence_text.split('\n'):
        text_object2.textLine(line)
    c.drawText(text_object2)

    c.showPage()
    c.save()

    response = send_file(pdf_path, as_attachment=True)
    try:
        os.remove(pdf_path)
    except Exception as e:
        print(f"Error deleting PDF: {e}")

    return response
