from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models import Report, User
from app.utils.suspect_utils import analyze_evidence
from app.utils.translate_utils import translate_bundle
from app.utils.pdf_tools import extract_text_from_pdf
import os
import json
from app.utils.legal_references import LEGAL_REFERENCES
import json
from app.utils.legal_references import LEGAL_REFERENCES

report = Blueprint("report", __name__)

# ---------------- Submit Report ----------------
@report.route("/submit-report", methods=["POST"])
@jwt_required()
def submit_report():
    user_id = get_jwt_identity()
    data = request.form.to_dict() or request.get_json() or {}

    # 🔹 Get user inputs
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    address = data.get("address")
    email = data.get("email")
    phone = data.get("phone")
    state = data.get("state")
    city = data.get("city")
    complaint_category = data.get("complaint_category")
    incident_date = data.get("incident_date")
    delay_in_reporting = data.get("delay_in_reporting")
    platform = data.get("platform")
    description = data.get("description")

    if not description:
        return jsonify({"error": "Description is required"}), 400

    # 🔹 Language detection + translation
    desc_bundle = translate_bundle(description)

    # 🔹 Handle file evidence
    evidence_file = request.files.get("evidence_file")
    file_path = None
    if evidence_file:
        uploads_dir = "uploads"
        os.makedirs(uploads_dir, exist_ok=True)
        file_path = os.path.join(uploads_dir, evidence_file.filename)
        evidence_file.save(file_path)

    # 🔹 Create report entry
    new_report = Report(
        user_id=user_id,
        first_name=first_name,
        last_name=last_name,
        address=address,
        email=email,
        phone=phone,
        state=state,
        city=city,
        complaint_category=complaint_category,
        incident_date=incident_date,
        delay_in_reporting=delay_in_reporting,
        platform=platform,
        description=desc_bundle["translated"],
        evidence_file=file_path,
        created_at=datetime.utcnow()
    )

    db.session.add(new_report)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Report submitted successfully",
        "report": new_report.to_dict(),
    }), 201


# ---------------- Get Report (JWT-protected) ----------------
@report.route("/get-report/<int:report_id>", methods=["GET"])
@jwt_required()
def get_report(report_id):
    user_id = get_jwt_identity()
    report_obj = Report.query.filter_by(id=report_id, user_id=user_id).first()

    if not report_obj:
        return jsonify({"status": "error", "message": "Report not found or unauthorized"}), 404

    return jsonify({"status": "success", "report": report_obj.to_dict()}), 200


# ---------------- Analyze Report (JWT-protected) ----------------
@report.route("/analyze-report/<int:report_id>", methods=["POST"])
@jwt_required()
def analyze_report(report_id):
    user_id = get_jwt_identity()
    report_obj = Report.query.filter_by(id=report_id, user_id=user_id).first()

    if not report_obj:
        return jsonify({"status": "error", "message": "Report not found or unauthorized"}), 404

    # 🔹 Forensic analysis
    text_from_pdf = ""
    if report_obj.evidence_file and report_obj.evidence_file.endswith(".pdf"):
        text_from_pdf = extract_text_from_pdf(report_obj.evidence_file)
    
    analysis_result = analyze_evidence(text=report_obj.description + "\n" + text_from_pdf, file_path=report_obj.evidence_file)
    
    forensic_summary = {
        "summary": analysis_result.get("summary", ""),
        "suspect_profile": analysis_result.get("suspect_profile", "Unknown"),
        "key_clues": analysis_result.get("clues", []),
    }

    report_obj.set_json_field("forensic_summary", forensic_summary)
    report_obj.set_json_field("forensic_details", analysis_result)
    report_obj.status = "analyzed"

    db.session.commit()

    return jsonify({"status": "success", "message": "Report analyzed successfully", "analysis": analysis_result}), 200



