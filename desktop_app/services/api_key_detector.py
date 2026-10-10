import re

def detect_provider(key: str) -> str:
    key = key.strip()
    if key.startswith("AIza"):
        return "Gemini"
    if key.startswith("gsk_"):
        return "Groq"
    if key.startswith("nvapi-"):
        return "NVIDIA"
    if key.startswith("sk-or-"):
        return "OpenRouter"
    if re.fullmatch(r"[a-f0-9]{64}", key):
        return "Together AI"
    if key.startswith("sk-"):
        return "OpenAI"
    return "Unknown"
