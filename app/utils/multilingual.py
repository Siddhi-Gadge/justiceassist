from langdetect import detect
from transformers import MarianMTModel, MarianTokenizer
import logging

# Optional: Fallback to OpenAI/Gemini or any external service
try:
    import openai
    USE_API = True
except ImportError:
    USE_API = False

logging.basicConfig(level=logging.INFO)

class Translator:
    def __init__(self):
        # Load MarianMT for translation (English ↔ target)
        # Example: English ↔ Hindi
        self.models = {}
        self.tokenizers = {}
        
        # Preload common languages (extendable)
        self.supported_pairs = {
            "hi": "Helsinki-NLP/opus-mt-en-hi",
            "ta": "Helsinki-NLP/opus-mt-en-ta",
            "es": "Helsinki-NLP/opus-mt-en-es"
        }

    def _load_model(self, lang):
        if lang not in self.models:
            model_name = self.supported_pairs.get(lang)
            if not model_name:
                raise ValueError(f"Language {lang} not supported offline")
            self.tokenizers[lang] = MarianTokenizer.from_pretrained(model_name)
            self.models[lang] = MarianMTModel.from_pretrained(model_name)

    def detect_language(self, text: str) -> str:
        """Detects the input language using langdetect"""
        try:
            return detect(text)
        except Exception as e:
            logging.error(f"Language detection failed: {e}")
            return "en"

    def translate(self, text: str, target_lang: str = "en") -> str:
        """Translate text into target language"""
        if not text:
            return text
        
        if target_lang == "en":
            # If text is already English, skip detection
            src_lang = self.detect_language(text)
            if src_lang == "en":
                return text
        else:
            src_lang = "en"

        try:
            # Offline MarianMT
            self._load_model(target_lang)
            tokenizer = self.tokenizers[target_lang]
            model = self.models[target_lang]

            inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
            translated = model.generate(**inputs)
            return tokenizer.decode(translated[0], skip_special_tokens=True)

        except Exception as e:
            logging.warning(f"Offline translation failed, fallback to API. Error: {e}")
            if USE_API:
                return self._api_translate(text, target_lang)
            return text  # Fallback: return original

    def _api_translate(self, text: str, target_lang: str) -> str:
        """Fallback API-based translation (OpenAI, Gemini, etc.)"""
        try:
            # Example with OpenAI GPT
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"Translate this text into {target_lang}."},
                    {"role": "user", "content": text}
                ]
            )
            return resp["choices"][0]["message"]["content"]
        except Exception as e:
            logging.error(f"API translation failed: {e}")
            return text
