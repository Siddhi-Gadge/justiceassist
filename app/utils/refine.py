import re
from datetime import datetime

def refine_extracted_text(text):
    refined_data = {
        "phone_numbers": extract_phone_numbers(text),
        "emails": extract_emails(text),
        "upi_ids": extract_upi_ids(text),
        "dates": extract_dates(text),
        "amounts": extract_amounts(text),
        "key_sentences": extract_key_sentences(text),
    }
    return refined_data


def extract_phone_numbers(text):
    # phone numbers
    return re.findall(r'(?:(?:\+91[-\s]?)?|0)?[789]\d{9}', text)


def extract_emails(text):
    return re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)


def extract_upi_ids(text):
    return re.findall(r'\b\w+@\w+\b', text)


def extract_dates(text):
    # Finds date patterns
    date_patterns = re.findall(r'\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}', text)
    date_formats = []
    for d in date_patterns:
        try:
            dt = datetime.strptime(d, "%d/%m/%Y")
            date_formats.append(dt.strftime("%Y-%m-%d"))
        except:
            continue
    return date_formats


def extract_amounts(text):
    return re.findall(r'₹\s?\d+(?:,\d{3})*(?:\.\d+)?', text)


def extract_key_sentences(text):
    key_sentences = []
    for line in text.split("\n"):
        if any(keyword in line.lower() for keyword in ["fraud", "scam", "lost", "transaction", "complaint"]):
            key_sentences.append(line.strip())
    return key_sentences[:5] 
