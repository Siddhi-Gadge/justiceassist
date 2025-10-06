from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Report

dashboard = Blueprint("dashboard", __name__)

@dashboard.route("/dashboard", methods=["GET"])
@jwt_required()
def get_dashboard():
    user_id = get_jwt_identity()
    
    # Fetch user reports
    reports = Report.query.filter_by(user_id=user_id).order_by(Report.created_at.desc()).all()

    dashboard_reports = []
    category_counts = {}

    for r in reports:
        # For SQLite, use get_json_field for JSON fields
        suspect = r.suspect_guess
        summary = r.get_json_field("clues") or []

        dashboard_reports.append({
            "report_id": r.id,
            "title": r.title,
            "incident_type": r.incident_type,
            "date_of_incident": r.date_of_incident,
            "location": r.location,
            "status": r.status,
            "suspect_guess": suspect,
            "summary": summary[0] if summary else ""  # first clue as quick summary
        })

        cat = suspect or "Unknown"
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return jsonify({
        "status": "success",
        "total_reports": len(reports),
        "category_counts": category_counts,
        "reports": dashboard_reports
    }), 200
