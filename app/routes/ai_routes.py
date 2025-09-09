from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
import os
from dotenv import load_dotenv
import google.generativeai as genai
import openai
from werkzeug.utils import secure_filename
from app.utils.suspect_utils import analyze_evidence

load_dotenv()

gemini_key = os.getenv("GOOGLE_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")

if gemini_key:
    genai.configure(api_key=gemini_key)

if openai_key:
    openai.api_key = openai_key

ai = Blueprint('ai', __name__)
UPLOAD_FOLDER = "uploads"

# --------- GET GUIDANCE ----------
@ai.route('/get-guidance', methods=['POST'])
@jwt_required()
def get_guidance():
    data = request.get_json()
    user_query = data.get("query", "")

    if not user_query:
        return jsonify({"status": "error", "error": "Query is required"}), 400

    prompt = f"""
    You are a cybercrime assistant. A user submitted this incident: 
    \"{user_query}\"

    Based on this, give:
    - Personalized and practical steps they should take
    - Safety tips based on the context
    - Relevant official links or contacts (if applicable)

    Keep it short, clear, and victim-friendly.
    """

    # 1️⃣ Try Gemini
    if gemini_key:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            guidance_text = getattr(response, "text", None)

            if not guidance_text and hasattr(response, "candidates"):
                guidance_text = response.candidates[0].content.parts[0].text

            if guidance_text:
                return jsonify({
                    "status": "success",
                    "provider": "Gemini",
                    "guidance": guidance_text
                }), 200
        except Exception as e:
            print(f"Gemini failed: {e}")

    # 2️⃣ Fallback to OpenAI
    if openai_key:
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful cybercrime reporting assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            guidance_text = completion.choices[0].message["content"]
            return jsonify({
                "status": "success",
                "provider": "OpenAI",
                "guidance": guidance_text
            }), 200
        except Exception as e:
            print(f"OpenAI failed: {e}")

    # 3️⃣ If both fail
    return jsonify({
        "status": "error",
        "error": "Both Gemini and OpenAI services failed. Please try again later."
    }), 500


# --------- SUSPECT GUESS ----------
@ai.route('/guess-suspect', methods=['POST'])
@jwt_required()
def guess_suspect():
    # Accept both text evidence and file upload
    description = request.form.get("description", "")
    file = request.files.get("file")
    file_path = None

    if not description and not file:
        return jsonify({
            "status": "error",
            "error": "Either text or file evidence is required"
        }), 400

    # Save uploaded file temporarily
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

    # Run forensic analysis pipeline
    result = analyze_evidence(description, file_path)

    # Clean up uploaded file
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

    return jsonify({
        "status": "success",
        "analysis": result
    }), 200
