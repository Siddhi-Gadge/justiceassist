from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from datetime import datetime
from app.models import Report, User
import os

# Simple mapping for legal references (flexible, can expand later)
LEGAL_REFERENCES = {
    "Phishing Attempt": ["IT Act 2000 - Sec 66C (Identity Theft)", "IPC Sec 420 (Cheating & Fraud)"],
    "Financial Fraud": ["IT Act 2000 - Sec 66D (Cheating by Personation)", "IPC Sec 415/420 (Cheating)"],
    "Caller/SMS Spoofing": ["IT Act 2000 - Sec 66 (Computer-related Offenses)"],
    "Ransomware Attack": ["IT Act 2000 - Sec 66F (Cyber Terrorism)", "IPC Sec 383 (Extortion)"],
    "System Hacking": ["IT Act 2000 - Sec 66 (Unauthorized Access)", "IPC Sec 379 (Theft)"],
    "Malware Infection": ["IT Act 2000 - Sec 43 (Damage to Computer)", "Sec 66 (Computer Hacking)"],
    "Cyber Harassment/Extortion": ["IPC Sec 354D (Stalking)", "IPC Sec 503 (Criminal Intimidation)"],
    "Identity Theft": ["IT Act 2000 - Sec 66C", "IPC Sec 419 (Impersonation)"],
    "Data Breach": ["IT Act 2000 - Sec 72 (Breach of Confidentiality)", "Sec 43 (Unauthorized Access)"],
    "Other / Unknown": ["Further investigation required under IT Act & IPC"]
}


def generate_case_pdf(report: Report, user: User, output_dir="generated_pdfs"):
    
    from app.utils.suspect_utils import analyze_evidence

    """Generate structured PDF report with forensic + legal analysis"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    filename = f"{output_dir}/case_report_{report.id}.pdf"

    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("Cybercrime Case Report", styles["Title"]))
    story.append(Spacer(1, 12))

    # Case Metadata
    story.append(Paragraph(f"Case ID: {report.id}", styles["Normal"]))
    story.append(Paragraph(f"Submitted By: User {user.username}", styles["Normal"]))
    story.append(Paragraph(f"Date Submitted: {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Case Details
    story.append(Paragraph("Case Details", styles["Heading2"]))
    story.append(Paragraph(f"Title: {report.title}", styles["Normal"]))
    story.append(Paragraph(f"Type: {report.incident_type}", styles["Normal"]))
    story.append(Paragraph(f"Date of Incident: {report.date_of_incident}", styles["Normal"]))
    story.append(Paragraph(f"Location: {report.location}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Description", styles["Heading2"]))
    story.append(Paragraph(report.description, styles["Normal"]))
    story.append(Spacer(1, 12))

    # Evidence Analysis
    story.append(Paragraph("Forensic Evidence Analysis", styles["Heading2"]))
    evidence_text = report.evidence_text or "No evidence text provided"
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

    return filename
