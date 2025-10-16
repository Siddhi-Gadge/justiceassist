import os
import fitz  # PyMuPDF
import pytesseract
from google.cloud import vision
from google.api_core.exceptions import GoogleAPICallError, PermissionDenied

def extract_text_from_pdf(filepath):
    # Check for Google Cloud credentials
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            return extract_text_with_google_vision(filepath)
        except (GoogleAPICallError, PermissionDenied, Exception) as e:
            print(f"Google Cloud Vision failed: {e}. Falling back to Tesseract.")
            return extract_text_with_tesseract(filepath)
    else:
        print("Google Cloud credentials not found. Using Tesseract.")
        return extract_text_with_tesseract(filepath)

def extract_text_with_google_vision(filepath):
    client = vision.ImageAnnotatorClient()
    with open(filepath, "rb") as f:
        content = f.read()
    
    input_config = vision.InputConfig(content=content, mime_type='application/pdf')
    features = [vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)]

    request = vision.AnnotateFileRequest(
        input_config=input_config,
        features=features,
    )

    response = client.annotate_file(request=request)
    
    all_text = ""
    for annotation in response.responses:
        all_text += annotation.full_text_annotation.text

    return all_text.strip()

def extract_text_with_tesseract(filepath):
    try:
        doc = fitz.open(filepath)
        all_text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
            img_bytes = pix.tobytes("png")
            text = pytesseract.image_to_string(img_bytes)
            all_text += text
        return all_text.strip()
    except Exception as e:
        return f"[Error extracting PDF text with Tesseract: {e}]"
