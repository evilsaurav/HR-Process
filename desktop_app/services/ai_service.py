import requests

def test_connection(provider: str, api_key: str):
    """Returns (success: bool, message: str)"""
    try:
        if provider == "Gemini":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            list(genai.list_models())
            return True, "Gemini connected successfully"

        elif provider == "Groq":
            r = requests.get("https://api.groq.com/openai/v1/models",
                              headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
            return (True, "Groq connected") if r.status_code == 200 else (False, f"Groq error: {r.status_code}")

        elif provider == "NVIDIA":
            r = requests.get("https://integrate.api.nvidia.com/v1/models",
                              headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
            return (True, "NVIDIA connected") if r.status_code == 200 else (False, f"NVIDIA error: {r.status_code}")

        elif provider == "OpenRouter":
            r = requests.get("https://openrouter.ai/api/v1/models",
                              headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
            return (True, "OpenRouter connected") if r.status_code == 200 else (False, f"Error: {r.status_code}")

        elif provider == "Together AI":
            r = requests.get("https://api.together.xyz/v1/models",
                              headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
            return (True, "Together AI connected") if r.status_code == 200 else (False, f"Error: {r.status_code}")

        elif provider == "OpenAI":
            r = requests.get("https://api.openai.com/v1/models",
                              headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
            return (True, "OpenAI connected") if r.status_code == 200 else (False, f"Error: {r.status_code}")

        return False, "Unknown provider - cannot verify"
    except Exception as e:
        return False, str(e)
