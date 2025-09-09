from PIL import Image
import pytesseract
import fitz  # PyMuPDF
import os

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        text = extract_text_from_pdf(file_path)
        if not text.strip():  # If empty, try OCR
            text = ocr_pdf(file_path)
        return text
    elif ext in ['.jpg', '.jpeg', '.png']:
        return extract_text_from_image(file_path)
    else:
        return "Unsupported file type."

def extract_text_from_pdf(path):
    text = ""
    with fitz.open(path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def ocr_pdf(path):
    text = ""
    with fitz.open(path) as doc:
        for page_num in range(len(doc)):
            pix = doc[page_num].get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text += pytesseract.image_to_string(img)
    return text

def extract_text_from_image(path):
    return pytesseract.image_to_string(Image.open(path))
