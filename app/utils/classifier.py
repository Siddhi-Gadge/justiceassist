from transformers import pipeline

# HuggingFace zero-shot classifier 

classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

CATEGORIES = [
    "Phishing",
    "Banking Fraud",
    "Social Media Hacking",
    "Cyberbullying",
    "Identity Theft",
    "Other"
]

def classify_text(text: str) -> dict:
    """
    Classify evidence text into one of the predefined categories.

    Returns:
        dict with category, confidence, and explanation
    """
    if not text or not isinstance(text, str):
        return {
            "category": "Unknown",
            "confidence": 0.0,
            "explanation": "No valid evidence text provided."
        }

    result = classifier(text, candidate_labels=CATEGORIES)

    top_category = result["labels"][0]
    top_score = float(result["scores"][0])

    return {
        "category": top_category,
        "confidence": round(top_score, 2),
        "explanation": f"Classified as '{top_category}' with confidence {round(top_score,2)}."
    }
