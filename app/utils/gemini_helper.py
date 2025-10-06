# app/utils/gemini_helper.py
import google.generativeai as genai
import os
from app.utils.classifier import classify_incident

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash") 

def get_guidance(text):
    
    category = classify_incident(text)

    prompt = f"""
    A user has reported a cybercrime.
    Category: {category}
    Description: {text}

    Please provide:
    1. Next steps for the victim
    2. Relevant legal sections (India)
    3. Where to report officially
    Return concise guidance in JSON format.
    """

    response = model.generate_content(prompt)
    return {
        "category": category,
        "guidance": response.text if response and response.text else "No response"
    }

def guess_suspect(text):
    prompt = f"""
    Analyze the following report/evidence:
    {text}

    Identify possible suspect characteristics or technical clues 
    (e.g., spoofing, phishing style, fraud patterns, IP hints).
    Return structured JSON.
    """
    response = model.generate_content(prompt)
    return response.text if response and response.text else "No response"
