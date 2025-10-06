# app/utils/suspect_utils.py
import re
import os
import socket
import hashlib
import json
import tldextract
import whois
import dns.resolver
from ipwhois import IPWhois

# Optional AI providers (Gemini / OpenAI). They are used only if API keys present.
import google.generativeai as genai
import openai

# Configure keys if present
if os.getenv("GOOGLE_API_KEY"):
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
if os.getenv("OPENAI_API_KEY"):
    openai.api_key = os.getenv("OPENAI_API_KEY")


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


# -----------------------
# Helpers
# -----------------------
def safe_json_parse(s):
    """Try to parse a JSON string; on failure return raw string wrapped in dict."""
    if not s:
        return {}
    if isinstance(s, dict):
        return s
    try:
        return json.loads(s)
    except Exception:
        # Try to extract JSON substring if model returned extra text
        try:
            start = s.find("{")
            end = s.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(s[start:end+1])
        except Exception:
            pass
    # fallback: return raw text in ai_raw
    return {"ai_raw": s}


# -----------------------
# Artifact extraction
# -----------------------
def extract_artifacts(text: str):
    """Extract emails, urls, ips, phones from free text. Returns standardized keys."""
    text = text or ""
    artifacts = {}

    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    if emails:
        artifacts["emails"] = list(dict.fromkeys(emails))  # dedupe, preserve order

    urls = re.findall(r"http[s]?://[^\s'\"<>]+", text)
    if urls:
        artifacts["urls"] = list(dict.fromkeys(urls))

    ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
    # filter out invalid IP octets >255
    valid_ips = []
    for ip in ips:
        parts = ip.split(".")
        if all(0 <= int(p) <= 255 for p in parts):
            valid_ips.append(ip)
    if valid_ips:
        artifacts["ips"] = list(dict.fromkeys(valid_ips))

    phones = re.findall(r"\+?\d[\d\s\-\(\)]{7,}\d", text)
    if phones:
        artifacts["phones"] = list(dict.fromkeys(phones))

    return artifacts


# -----------------------
# Rule-based classification
# -----------------------
def rule_based_classification(text: str):
    if not text:
        return None, []

    t = text.lower()
    if re.search(r"\botp\b|password|login|bank|paypal", t):
        return "Phishing Attempt", ["Suspicious credential-related request detected"]

    if re.search(r"\bupi\b|wallet|transaction|money|payment", t):
        return "Financial Fraud", ["Suspicious financial terms detected"]

    if re.search(r"spoof|caller id|fake number|masking", t):
        return "Caller/SMS Spoofing", ["Caller ID or number spoofing indicated"]

    if re.search(r"ransom|bitcoin|encrypt|decrypt", t):
        return "Ransomware Attack", ["Mentions of ransom or file encryption"]

    if re.search(r"hacked|compromise|breach|unauthorized", t):
        return "System Hacking", ["Signs of unauthorized access"]

    if re.search(r"malware|virus|trojan|spyware", t):
        return "Malware Infection", ["Indicators of malware detected"]

    if re.search(r"harass|threat|blackmail|abuse", t):
        return "Cyber Harassment/Extortion", ["Threatening or abusive language found"]

    return None, []


# -----------------------
# AI fallback (returns dict)
# -----------------------
def ai_fallback(text: str):
    """Ask configured AI model to classify and return JSON-like dict."""
    prompt = f"""
You are a digital forensic analyst.
Classify the following evidence into one of: {', '.join(CATEGORIES)}.
Provide a JSON object with keys: suspect_profile (string), clues (list of strings), summary (string), legal (optional list).
Evidence:
{text}
Respond only with valid JSON.
"""

    # Try Gemini first (if key present)
    if os.getenv("GOOGLE_API_KEY"):
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            # attempt to get text content
            text_out = None
            if hasattr(response, "text"):
                text_out = response.text
            elif hasattr(response, "candidates"):
                text_out = response.candidates[0].content.parts[0].text
            if text_out:
                return safe_json_parse(text_out)
        except Exception:
            pass

    # Fallback to OpenAI if key present
    if os.getenv("OPENAI_API_KEY"):
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a cyber forensic assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            text_out = completion.choices[0].message["content"]
            return safe_json_parse(text_out)
        except Exception:
            pass

    # Final fallback: safe default
    return {"summary": "Unable to analyze evidence", "clues": [], "suspect_profile": "Unknown"}


# -----------------------
# URL / Domain / IP inspection
# -----------------------
def inspect_urls(urls):
    """
    For each URL, extract domain, resolve IPs (A records), run whois on domain and collect DNS records.
    Returns list of dicts for each URL.
    """
    results = []
    if not urls:
        return results

    for url in urls:
        entry = {"url": url, "domain": None, "resolved_ips": [], "whois": None, "dns": {}, "error": None}
        try:
            # extract domain robustly
            ext = tldextract.extract(url)
            domain = ".".join(part for part in [ext.domain, ext.suffix] if part)
            entry["domain"] = domain or None

            # DNS A records (resolve host)
            try:
                answers = dns.resolver.resolve(domain, "A", lifetime=5)
                resolved = [rdata.to_text() for rdata in answers]
                entry["resolved_ips"] = resolved
            except Exception:
                # try socket fallback for simple resolution
                try:
                    host = re.sub(r"^https?://", "", url).split("/")[0]
                    ip = socket.gethostbyname(host)
                    entry["resolved_ips"] = [ip]
                except Exception:
                    entry["resolved_ips"] = []

            # WHOIS for domain
            try:
                w = whois.whois(domain)
                # normalize some fields
                creation = w.creation_date
                expiration = w.expiration_date
                if isinstance(creation, list):
                    creation = creation[0]
                if isinstance(expiration, list):
                    expiration = expiration[0]
                whois_dict = {
                    "registrar": getattr(w, "registrar", None),
                    "creation_date": str(creation) if creation else None,
                    "expiration_date": str(expiration) if expiration else None,
                    "country": getattr(w, "country", None),
                    "emails": list(w.emails) if getattr(w, "emails", None) else []
                }
                entry["whois"] = whois_dict
            except Exception as e:
                entry["whois"] = {"error": f"whois failed: {str(e)}"}

            # DNS records: MX, NS, TXT
            try:
                for rtype in ("MX", "NS", "TXT"):
                    try:
                        answers = dns.resolver.resolve(domain, rtype, lifetime=5)
                        entry["dns"][rtype] = [r.to_text() for r in answers]
                    except Exception:
                        entry["dns"][rtype] = []
            except Exception:
                pass

        except Exception as e:
            entry["error"] = str(e)

        results.append(entry)
    return results


def inspect_ips(ips):
    """Run ipwhois RDAP lookup and reverse DNS where possible."""
    results = []
    if not ips:
        return results

    for ip in ips:
        entry = {"ip": ip, "rdap": None, "asn": None, "reverse_dns": None, "error": None}
        try:
            # RDAP / IPWhois
            try:
                obj = IPWhois(ip)
                rd = obj.lookup_rdap(asn_methods=["whois"])
                entry["rdap"] = {
                    "network": rd.get("network", {}),
                    "asn": rd.get("asn"),
                    "asn_country_code": rd.get("asn_country_code"),
                    "asn_description": rd.get("asn_description")
                }
                entry["asn"] = rd.get("asn")
            except Exception as e:
                entry["rdap"] = {"error": str(e)}

            # reverse DNS
            try:
                entry["reverse_dns"] = socket.gethostbyaddr(ip)[0]
            except Exception:
                entry["reverse_dns"] = None

        except Exception as e:
            entry["error"] = str(e)
        results.append(entry)
    return results


# -----------------------
# File hashing
# -----------------------
def get_file_hash(file_path):
    """Return dict with MD5 and SHA256 (and fallback error handling)."""
    try:
        md5 = hashlib.md5()
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
                sha256.update(chunk)
        return {"md5": md5.hexdigest(), "sha256": sha256.hexdigest()}
    except Exception as e:
        return {"error": str(e)}


# -----------------------
# Main analyzer (hybrid)
# -----------------------
def analyze_evidence(text: str = "", file_path: str = None):
    """
    Unified forensic pipeline.
    Returns a dict containing:
      - summary, suspect_profile, clues
      - artifacts (emails, urls, ips, phones)
      - url_analysis (list), ip_analysis (list)
      - file_hash (dict) if file provided
      - raw ai output if AI was used and not parsable
    """
    text = text or ""
    result = {}

    # 1) Extract artifacts
    artifacts = extract_artifacts(text)
    result["artifacts"] = artifacts

    # 2) Rule-based classification
    profile, clues = rule_based_classification(text)

    if profile:
        result.update({
            "summary": f"Possible suspect activity: {profile}",
            "suspect_profile": profile,
            "clues": clues
        })
    else:
        # AI fallback
        ai_out = ai_fallback(text)
        # ensure a dict
        if isinstance(ai_out, dict):
            result.update(ai_out)
        else:
            # safe parse if string
            parsed = safe_json_parse(ai_out)
            result.update(parsed if isinstance(parsed, dict) else {"ai_raw": ai_out})

        # ensure keys exist
        result.setdefault("summary", result.get("summary", ""))
        result.setdefault("suspect_profile", result.get("suspect_profile", "Unknown"))
        result.setdefault("clues", result.get("clues", []))

    # 3) File hashing (if provided)
    if file_path:
        result["file_hash"] = get_file_hash(file_path)

    # 4) URL analysis (resolve domain, whois, dns)
    if artifacts.get("urls"):
        result["url_analysis"] = inspect_urls(artifacts.get("urls", []))

        # correlate resolved IPs with ip inspection
        resolved_ips = []
        for u in result.get("url_analysis", []):
            resolved_ips.extend(u.get("resolved_ips", []))
        resolved_ips = list(dict.fromkeys(resolved_ips))
        if resolved_ips:
            # merge with existing artifacts ips if not present
            existing_ips = set(artifacts.get("ips", []))
            for rip in resolved_ips:
                if rip not in existing_ips:
                    artifacts.setdefault("ips", []).append(rip)
            result["ip_analysis"] = inspect_ips(artifacts.get("ips", []))

    # 5) IP analysis (if ips found and not already processed)
    if artifacts.get("ips") and "ip_analysis" not in result:
        result["ip_analysis"] = inspect_ips(artifacts.get("ips", []))

    # 6) Final cleanup: ensure fields exist
    result.setdefault("artifacts", artifacts)
    result.setdefault("clues", result.get("clues", []))
    result.setdefault("summary", result.get("summary", "No clear suspect profile"))
    result.setdefault("suspect_profile", result.get("suspect_profile", "Unknown"))

    return result
