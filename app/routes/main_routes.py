from flask import Blueprint, request, jsonify
from app.models import Report
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

@main.route('/submit-report', methods=['POST'])
def submit_report():
    data = request.get_json()
    current_user_id = get_jwt_identity()

    try:
        report = Report(
            title=data.get('title'),
            incident_type=data.get('incident_type'),
            description=data.get('description'),
            date_of_incident=data.get('date_of_incident'),
            location=data.get('location'),
            evidence_text=data.get('evidence_text'),   # optional
            suspect_guess=data.get('suspect_guess'),   # optional
            guidance=data.get('guidance'),             # optional
            status=data.get('status', 'submitted'),    # default if not provided
            created_at=datetime.utcnow(),
            user_id=current_user_id
        )

        db.session.add(report)
        db.session.commit()

        return jsonify({
            'message': 'Report submitted successfully',
            'report': report.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    
@main.route('/update-report/<int:report_id>', methods=['PUT'])
@jwt_required()
def update_report(report_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()

    # Fetch the report
    report = Report.query.filter_by(id=report_id, user_id=current_user_id).first()
    if not report:
        return jsonify({"error": "Report not found or access denied"}), 404

    # Update only provided fields
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
    