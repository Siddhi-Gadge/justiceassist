from flask import Blueprint, request, jsonify
from app.models import Report, User
from app import db
from app.utils import extract_text
from app.utils.refine import refine_extracted_text
import os
from datetime import datetime
from flask_jwt_extended import jwt_required, get_jwt_identity

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return jsonify({"message": "JusticeAssist backend is running."})

@main.route('/protected')
@jwt_required()
def protected():
    return jsonify(message="You are authenticated")

@main.route('/extract-text', methods=['POST'])
def extract_text_route():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty file name'}), 400

    upload_folder = 'uploads'
    os.makedirs(upload_folder, exist_ok=True)
    save_path = os.path.join(upload_folder, file.filename)
    file.save(save_path)

    text = extract_text(save_path)
    refined = refine_extracted_text(text)

    return jsonify({
        'extracted_text': text,
        'refined_evidence': refined
    })

@main.route("/submit-report", methods=["POST"])
@jwt_required()
def submit_report():
    try:
        # --- Raw data preview ---
        try:
            raw_preview = request.get_data()[:2000].decode("utf-8", errors="replace")
        except Exception:
            raw_preview = "<binary or unreadable>"

        content_type = request.headers.get("Content-Type") or request.content_type

        # --- Try JSON first (some clients send JSON) ---
        json_payload = request.get_json(silent=True)
        json_payload = json_payload if isinstance(json_payload, dict) else {}

        # --- Extract form and files as dicts ---
        form_dict = request.form.to_dict() if request.form else {}
        files_dict = request.files.to_dict() if request.files else {}

        # --- Normalize keys to lowercase for case-insensitivity ---
        normalized = {}
        normalized.update({k.lower(): v for k, v in json_payload.items()})
        normalized.update({k.lower(): v for k, v in form_dict.items()})
        normalized_files = {k.lower(): v for k, v in files_dict.items()}

        # --- Fallback: Accept single unnamed file if only one file sent ---
        if not normalized_files and request.files:
            first_file_key = next(iter(request.files.keys()))
            normalized_files[first_file_key.lower()] = request.files.get(first_file_key)

        # --- Extract fields from normalized dicts ---
        title = normalized.get("title")
        description = normalized.get("description")
        evidence_text = normalized.get("evidence_text", "")
        incident_type = normalized.get("incident_type")
        date_of_incident = normalized.get("date_of_incident")
        location = normalized.get("location")

        # --- Debug output if requested ---
        if request.args.get("debug"):
            return jsonify({
                "content_type": content_type,
                "raw_preview": raw_preview,
                "json_payload_keys": list(json_payload.keys()),
                "form_keys": list(form_dict.keys()),
                "files_keys": list(files_dict.keys()),
                "normalized_keys": list(normalized.keys()),
                "normalized_file_keys": list(normalized_files.keys())
            }), 200    

        # --- Validate required fields ---
        if not title or not description or not evidence_text:
            return jsonify({"error": "Title, description, and evidence_text are required"}), 400

        # --- Handle file upload ---
        evidence_file = normalized_files.get("evidence_file")
        file_path = None
        if evidence_file:
            upload_folder = "uploads/"
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, evidence_file.filename)
            evidence_file.save(file_path)
            print(f"📁 Evidence file saved to: {file_path}")

        # --- Run forensic analysis ---
        forensic_result = analyze_evidence(text=evidence_text, file_path=file_path)

        # --- Create report record ---
        user_id = get_jwt_identity()
        new_report = Report(
            title=title,
            incident_type=incident_type,
            description=description,
            date_of_incident=date_of_incident,
            location=location,
            evidence_text=evidence_text,
            forensic_analysis=forensic_result,
            user_id=user_id,
            created_at=datetime.utcnow()
        )

        db.session.add(new_report)
        db.session.commit()

        print("✅ Report successfully created!")

        return jsonify({
            "status": "success",
            "message": "Report submitted successfully",
            "report": new_report.to_dict(),
            "forensic_analysis": forensic_result
        }), 201

    except Exception as e:
        print("❌ Exception in /submit-report:", str(e))
        return jsonify({"error": str(e)}), 500

@main.route('/update-report/<int:report_id>', methods=['PUT'])
@jwt_required()
def update_report(report_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()

    # Fetch report
    
    report = Report.query.filter_by(id=report_id, user_id=current_user_id).first()
    if not report:
        return jsonify({"error": "Report not found or access denied"}), 404

    if 'status' in data:
        report.status = data['status']
    if 'description' in data:
        report.description = data['description']
    if 'evidence_text' in data:
        report.evidence_text = data['evidence_text']

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update report", "details": str(e)}), 500

    return jsonify({"message": "Report updated", "report": report.to_dict()}), 200
    