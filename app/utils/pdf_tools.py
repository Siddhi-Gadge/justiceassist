from PyPDF2 import PdfReader

def extract_text_from_pdf(filepath):
    try:
        reader = PdfReader(filepath)
        all_text = ""
        for page in reader.pages:
            all_text += page.extract_text() or ""
        return all_text.strip()
    except Exception as e:
        return f"[Error extracting PDF text: {e}]"
