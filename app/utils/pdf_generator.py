from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import os

def generate_pdf(report_data, forensic_data, output_path="generated_report.pdf", image_paths=None):
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # --- Report Header ---
    elements.append(Paragraph("<b>Cybercrime Incident Report</b>", styles["Title"]))
    elements.append(Spacer(1, 12))

    # --- Basic Report Info ---
    elements.append(Paragraph(f"<b>Title:</b> {report_data['title']}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Incident Type:</b> {report_data['incident_type']}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Date of Incident:</b> {report_data['date_of_incident']}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Location:</b> {report_data['location']}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # --- Evidence Text ---
    elements.append(Paragraph("<b>Evidence Text:</b>", styles["Heading2"]))
    elements.append(Paragraph(report_data.get("evidence_text", "Not provided."), styles["Normal"]))
    elements.append(Spacer(1, 12))

    # --- Forensic Analysis ---
    elements.append(Paragraph("<b>Forensic Summary:</b>", styles["Heading2"]))
    elements.append(Paragraph(forensic_data.get("summary", "N/A"), styles["Normal"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"<b>Suspect Profile:</b> {forensic_data.get('suspect_profile', 'Unknown')}", styles["Normal"]))
    clues = forensic_data.get("clues", [])
    if clues:
        elements.append(Paragraph("<b>Clues:</b>", styles["Heading2"]))
        for clue in clues:
            elements.append(Paragraph(f"- {clue}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # --- Artifacts ---
    elements.append(Paragraph("<b>Extracted Artifacts:</b>", styles["Heading2"]))
    artifacts = forensic_data.get("artifacts", {})
    for key, values in artifacts.items():
        if values:
            elements.append(Paragraph(f"<b>{key.capitalize()}</b>: {', '.join(values)}", styles["Normal"]))
    elements.append(Spacer(1, 24))

    # --- Evidence Attachments (Images) ---
    if image_paths:
        elements.append(PageBreak())
        elements.append(Paragraph("<b>Attached Screenshots / Evidence Files</b>", styles["Heading2"]))
        elements.append(Spacer(1, 12))

        for img_path in image_paths:
            if os.path.exists(img_path):
                try:
                    elements.append(Image(img_path, width=5*inch, height=3*inch))
                    elements.append(Spacer(1, 12))
                except Exception as e:
                    elements.append(Paragraph(f"Error rendering image {img_path}: {str(e)}", styles["Normal"]))
                
    # --- PDF Document Evidence ---
    if pdf_texts:
        elements.append(PageBreak())
        elements.append(Paragraph("<b>Document Evidence (PDF)</b>", styles["Heading2"]))
        for filename, content in pdf_texts.items():
            elements.append(Paragraph(f"<b>{filename}</b>", styles["Normal"]))
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(content[:3000] + ("..." if len(content) > 3000 else ""), styles["Normal"]))  # avoid overload
            elements.append(Spacer(1, 24))

    doc.build(elements)
    return output_path
