import re
import os
import openai
import google.generativeai as genai

# Load API keys from environment
openai.api_key = os.getenv("OPENAI_API_KEY")
if os.getenv("GOOGLE_API_KEY"):
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

CATEGORIES = [
    "Phishing Attempt",
    "Financial Fraud",
    "Caller/SMS Spoofing",
    "Ransomware Attack",
    "System Hacking",
    "Malware Infection",
    "Cyber Harassment/Extortion",
    "Identity Theft",
    "Data Breach",
    "Other / Unknown"
]

def rule_based_classification(text: str):
    """Quick keyword-based suspect classification."""
    if re.search(r"otp|password|login|bank", text, re.IGNORECASE):
        return "Phishing Attempt", ["Mentions credentials, OTP, or login data"]

    elif re.search(r"upi|wallet|transaction|money|payment", text, re.IGNORECASE):
        return "Financial Fraud", ["Suspicious financial terms detected"]

    elif re.search(r"spoof|caller id|fake number|masking", text, re.IGNORECASE):
        return "Caller/SMS Spoofing", ["Caller ID or number spoofing indicated"]

    elif re.search(r"ransom|bitcoin|encrypt|decrypt", text, re.IGNORECASE):
        return "Ransomware Attack", ["Mentions ransom or file encryption"]

    elif re.search(r"hacked|compromise|breach|unauthorized", text, re.IGNORECASE):
        return "System Hacking", ["Signs of unauthorized access"]

    elif re.search(r"malware|virus|trojan|spyware", text, re.IGNORECASE):
        return "Malware Infection", ["Indicators of malware detected"]

    elif re.search(r"harass|threat|blackmail|abuse", text, re.IGNORECASE):
        return "Cyber Harassment/Extortion", ["Threatening or abusive language found"]

    return None, []  # No clear match


def ai_fallback(text: str):
    """Use Gemini or OpenAI to classify if rules don't match."""
    prompt = f"""
    You are a digital forensic analyst.
    Analyze the following evidence and classify it into one of these categories:
    {", ".join(CATEGORIES)}

    Evidence:
    {text}

    Respond in JSON with:
    - suspect_profile: best matching category
    - clues: bullet points justifying classification
    - summary: one-sentence forensic summary
    """

    # Prefer Gemini
    if os.getenv("GOOGLE_API_KEY"):
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return response.candidates[0].content.parts[0].text
        except Exception as e:
            print(f"Gemini failed: {e}")

    # Fallback OpenAI
    if os.getenv("OPENAI_API_KEY"):
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a cyber forensic assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            return completion.choices[0].message["content"]
        except Exception as e:
            print(f"OpenAI failed: {e}")

    return {
        "summary": "Unable to analyze evidence",
        "clues": [],
        "suspect_profile": "Unknown"
    }


def analyze_evidence(text: str = "", file_path: str = None):
    """
    Hybrid analysis: first rule-based, then AI fallback.
    """

    # 1️⃣ Rule-based classification
    profile, clues = rule_based_classification(text)

    if profile:  # Found by rules
        result = {
            "summary": f"Possible suspect activity: {profile}",
            "clues": clues,
            "suspect_profile": profile
        }
    else:
        # 2️⃣ AI fallback
        ai_result = ai_fallback(text)
        result = ai_result if isinstance(ai_result, dict) else {"ai_raw": ai_result}

    # 3️⃣ File metadata stub
    if file_path:
        _, ext = os.path.splitext(file_path)
        if ext.lower() in [".jpg", ".png", ".pdf", ".docx"]:
            result.setdefault("clues", []).append(
                f"File evidence uploaded ({ext}) — potential forensic metadata"
            )

    return result