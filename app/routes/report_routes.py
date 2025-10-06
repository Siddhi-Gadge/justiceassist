from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models import Report, User
from app.utils.suspect_utils import analyze_evidence
from app.utils.translate_utils import translate_bundle
from app.utils.pdf_utils import generate_case_pdf
import os
import json
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from app.utils.legal_references import LEGAL_REFERENCES

report = Blueprint("report", __name__)

# ---------------- Submit Report ----------------
@report.route("/submit-report", methods=["POST"])
@jwt_required()
def submit_report():
    user_id = get_jwt_identity()
    data = request.form.to_dict() or request.get_json() or {}

    title = data.get("title")
    description = data.get("description")
    evidence_text = data.get("evidence_text", "")

    if not title or not description:
        return jsonify({"error": "Title and description are required"}), 400

    # 🔹 Language detection + translation
    desc_bundle = translate_bundle(description)
    evidence_bundle = translate_bundle(evidence_text)

    # 🔹 Handle file evidence
    evidence_file = request.files.get("evidence_file")
    file_path = None
    if evidence_file:
        uploads_dir = "uploads"
        os.makedirs(uploads_dir, exist_ok=True)
        file_path = os.path.join(uploads_dir, evidence_file.filename)
        evidence_file.save(file_path)

    # 🔹 Forensic analysis
    analysis_result = analyze_evidence(text=evidence_text, file_path=file_path)
    forensic_summary = {
        "summary": analysis_result.get("summary", ""),
        "suspect_profile": analysis_result.get("suspect_profile", "Unknown"),
        "key_clues": analysis_result.get("clues", []),
        "language_info": desc_bundle  # ✅ Added properly with comma
    }

    # 🔹 Create report entry
    new_report = Report(
        title=title,
        incident_type=data.get("incident_type"),
        description=desc_bundle["translated"],
        evidence_text=evidence_bundle["translated"],
        date_of_incident=data.get("date_of_incident"),
        location=data.get("location"),
        user_id=user_id,
        created_at=datetime.utcnow(),
        forensic_summary=json.dumps(forensic_summary),
        forensic_details=json.dumps(analysis_result)
    )

    db.session.add(new_report)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Report submitted successfully",
        "report": new_report.to_dict(),
        "translation": {
            "description": desc_bundle,
            "evidence_text": evidence_bundle
        },
        "forensic_summary": forensic_summary
    }), 201


# ---------------- Generate PDF (JWT-protected) ----------------
@report.route("/generate-report/<int:report_id>", methods=["GET"])
@jwt_required()
def generate_case_pdf(report_id):
    from app.utils.suspect_utils import analyze_evidence
    from reportlab.platypus import Image

    user_id = get_jwt_identity()
    report_obj = Report.query.filter_by(id=report_id, user_id=user_id).first()
    user_obj = User.query.get(user_id)

    if not report_obj:
        return jsonify({"status": "error", "message": "Report not found or unauthorized"}), 404

    # ✅ Standardized output dir (inside app/pdf_reports)
    output_dir = os.path.join("pdf_reports")
    os.makedirs(output_dir, exist_ok=True)

    filename = os.path.join(output_dir, f"case_report_{report_obj.id}.pdf")

    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("Cybercrime Case Report", styles["Title"]))
    story.append(Spacer(1, 12))

    # Case Metadata
    story.append(Paragraph(f"Case ID: {report_obj.id}", styles["Normal"]))
    story.append(Paragraph(f"Submitted By: User {user_obj.username}", styles["Normal"]))
    story.append(Paragraph(f"Date Submitted: {report_obj.created_at.strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Case Details
    story.append(Paragraph("Case Details", styles["Heading2"]))
    story.append(Paragraph(f"Title: {report_obj.title}", styles["Normal"]))
    story.append(Paragraph(f"Type: {report_obj.incident_type}", styles["Normal"]))
    story.append(Paragraph(f"Date of Incident: {report_obj.date_of_incident}", styles["Normal"]))
    story.append(Paragraph(f"Location: {report_obj.location}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Description", styles["Heading2"]))
    story.append(Paragraph(report_obj.description, styles["Normal"]))
    story.append(Spacer(1, 12))

    # Evidence Analysis
    story.append(Paragraph("Forensic Evidence Analysis", styles["Heading2"]))
    evidence_text = report_obj.evidence_text or "No evidence text provided"
    analysis = analyze_evidence(text=evidence_text)

    story.append(Paragraph(f"Summary: {analysis.get('summary', 'N/A')}", styles["Normal"]))
    story.append(Paragraph(f"Suspect Profile: {analysis.get('suspect_profile', 'Unknown')}", styles["Normal"]))
    story.append(Spacer(1, 6))

    # Clues
    if analysis.get("clues"):
        story.append(Paragraph("Clues Identified:", styles["Heading3"]))
        for clue in analysis["clues"]:
            story.append(Paragraph(f"- {clue}", styles["Normal"]))

    # Artifacts
    if analysis.get("artifacts"):
        story.append(Paragraph("Artifacts Extracted:", styles["Heading3"]))
        for k, v in analysis["artifacts"].items():
            story.append(Paragraph(f"{k}: {', '.join(v) if v else 'None'}", styles["Normal"]))

    story.append(Spacer(1, 12))

    # Evidence Images (optional future extension)
    image_paths = []  # you can populate this list later when file upload is handled
    if image_paths:
        story.append(Paragraph("Evidence Images", styles["Heading2"]))
        for img_path in image_paths:
            if os.path.exists(img_path):
                try:
                    story.append(Image(img_path, width=400, height=300))
                    story.append(Spacer(1, 12))
                except Exception as e:
                    story.append(Paragraph(f"Error displaying image {img_path}: {e}", styles["Normal"]))

    # Legal References
    profile = analysis.get("suspect_profile", "Other / Unknown")
    legal_refs = LEGAL_REFERENCES.get(profile, ["Further legal mapping required"])
    story.append(Paragraph("Relevant Legal Sections", styles["Heading2"]))
    for ref in legal_refs:
        story.append(Paragraph(f"- {ref}", styles["Normal"]))

    # Footer
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}", styles["Italic"]))

    doc.build(story)

    return send_file(filename, as_attachment=True)


# ---------------- Fetch Full Report Details ----------------
@report.route("/report/<int:report_id>", methods=["GET"])
@jwt_required()
def get_report(report_id):
    user_id = get_jwt_identity()
    report_obj = Report.query.filter_by(id=report_id, user_id=user_id).first()

    if not report_obj:
        return jsonify({"status": "error", "message": "Report not found or unauthorized"}), 404

    report_data = {
        "report_id": report_obj.id,
        "title": report_obj.title,
        "incident_type": report_obj.incident_type,
        "date_of_incident": report_obj.date_of_incident,
        "location": report_obj.location,
        "status": report_obj.status,
        "description": report_obj.description,
        "evidence_text": report_obj.evidence_text,
        "suspect_guess": report_obj.get_json_field("suspect_guess"),
        "clues": report_obj.get_json_field("clues"),
        "forensic_summary": report_obj.get_json_field("forensic_summary"),
        "created_at": report_obj.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }

    return jsonify({"status": "success", "report": report_data}), 200


# ---------------- Download PDF ----------------
@report.route("/download/<int:report_id>", methods=["GET"])
@jwt_required()
def download_report(report_id):
    user_id = get_jwt_identity()
    report_obj = Report.query.filter_by(id=report_id, user_id=user_id).first()

    if not report_obj:
        return jsonify({"error": "Report not found"}), 404

    # ✅ Same standardized path
    pdf_path = os.path.join("app", "pdf_reports", f"case_report_{report_id}.pdf")
    if not os.path.exists(pdf_path):
        return jsonify({"error": "PDF not generated yet"}), 404

    return send_file(pdf_path, as_attachment=True)
