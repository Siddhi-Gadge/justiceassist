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
        forensic_summary = r.get_json_field("forensic_summary")
        suspect = forensic_summary.get("suspect_profile") if forensic_summary else "Unknown"
        summary = forensic_summary.get("summary") if forensic_summary else ""

        dashboard_reports.append({
            "report_id": r.id,
            "description": r.description,
            "incident_date": r.incident_date,
            "status": r.status,
            "suspect_guess": suspect,
            "summary": summary
        })

        cat = suspect or "Unknown"
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return jsonify({
        "status": "success",
        "total_reports": len(reports),
        "category_counts": category_counts,
        "reports": dashboard_reports
    }), 200
