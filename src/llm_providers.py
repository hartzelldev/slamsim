import os
import json
import urllib.request
import urllib.error

def fetch_dynamic_models(provider_name, static_models):
    """
    Attempts to dynamically fetch available models for a given provider.
    Falls back to static_models on failure or if no key/public endpoint exists.
    """
    try:
        if provider_name == "OpenRouter":
            # OpenRouter model endpoint is public
            req = urllib.request.Request("https://openrouter.ai/api/v1/models", headers={"User-Agent": "SlamSim"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models_data = data.get("data", [])
                if models_data:
                    dynamic_models = []
                    for m in models_data:
                        m_id = m.get("id")
                        m_name = m.get("name", m_id)
                        if m_id:
                            dynamic_models.append({"id": m_id, "name": f"{m_name} ({m_id})"})
                    dynamic_models.sort(key=lambda x: x["name"].lower())
                    return dynamic_models

        elif provider_name == "Groq":
            api_key = os.getenv("SLAMSIM_GROQ_KEY") or os.getenv("GROQ_API_KEY")
            if api_key:
                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {api_key}", "User-Agent": "SlamSim"}
                )
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    models_data = data.get("data", [])
                    if models_data:
                        dynamic_models = [
                            {"id": m["id"], "name": m.get("id", m["id"])}
                            for m in models_data if "id" in m
                        ]
                        dynamic_models.sort(key=lambda x: x["name"].lower())
                        return dynamic_models

        elif provider_name == "OpenAI":
            api_key = os.getenv("SLAMSIM_OPENAI_KEY") or os.getenv("OPENAI_API_KEY")
            if api_key:
                req = urllib.request.Request(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}", "User-Agent": "SlamSim"}
                )
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    models_data = data.get("data", [])
                    if models_data:
                        chat_models = [
                            {"id": m["id"], "name": m["id"]}
                            for m in models_data
                            if "id" in m and (m["id"].startswith("gpt") or m["id"].startswith("o1") or m["id"].startswith("o3"))
                        ]
                        if chat_models:
                            chat_models.sort(key=lambda x: x["name"].lower())
                            return chat_models
    except Exception as e:
        print(f"Dynamic model fetch failed for {provider_name}: {e}")

    return static_models
