# app/utils/translate_utils.py

from deep_translator import GoogleTranslator

def translate_bundle(text: str, target_lang: str = "en") -> dict:
    """
    Detects language and translates text to target language (default: English).
    Returns a simple dictionary with detected language and translated text.
    """
    if not text:
        return {"detected_lang": None, "translated": ""}

    try:
        # Detect source language
        detected_lang = GoogleTranslator().detect(text)

        # Translate to target language if needed
        if detected_lang != target_lang:
            translated_text = GoogleTranslator(source='auto', target=target_lang).translate(text)
        else:
            translated_text = text

        return {
            "detected_lang": detected_lang,
            "translated": translated_text
        }

    except Exception as e:
        # fallback: return original text
        return {
            "detected_lang": None,
            "translated": text
        }
