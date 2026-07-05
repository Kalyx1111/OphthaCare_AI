"""
Multi-Provider AI Module v2.0
==============================
6 real AI providers — all make live HTTP calls to official APIs.
No dummy/mock responses. Falls back gracefully when offline or key missing.

Providers:
  1. anthropic  — Claude (claude-sonnet-4-20250514)
  2. openai     — ChatGPT (gpt-4o)
  3. gemini     — Gemini (gemini-2.0-flash) via Google AI Studio
  4. grok       — Grok (grok-2-latest) via xAI
  5. deepseek   — DeepSeek (deepseek-chat)
  6. mistral    — Mistral AI (mistral-large-latest)

Security:
  - API keys passed per-call, never stored in module
  - All keys sanitised before use
  - Timeout enforced on every request
  - Error messages never echo back raw API keys
"""

import os
import json

try:
    import requests as req_lib
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False


PROVIDERS = {
    "anthropic": {
        "label": "Claude (Anthropic)",
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-20250514",
        "key_prefix": "sk-ant-",
        "get_key_url": "https://console.anthropic.com",
        "icon": "&#128995;",
    },
    "openai": {
        "label": "ChatGPT (OpenAI)",
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
        "key_prefix": "sk-",
        "get_key_url": "https://platform.openai.com/api-keys",
        "icon": "&#129001;",
    },
    "gemini": {
        "label": "Gemini (Google)",
        "env_key": "GEMINI_API_KEY",
        "default_model": "gemini-2.0-flash",
        "key_prefix": "AIza",
        "get_key_url": "https://aistudio.google.com/apikey",
        "icon": "&#128309;",
    },
    "grok": {
        "label": "Grok (xAI)",
        "env_key": "GROK_API_KEY",
        "default_model": "grok-2-latest",
        "key_prefix": "xai-",
        "get_key_url": "https://console.x.ai",
        "icon": "&#9899;",
    },
    "deepseek": {
        "label": "DeepSeek",
        "env_key": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
        "key_prefix": "sk-",
        "get_key_url": "https://platform.deepseek.com/api_keys",
        "icon": "&#128308;",
    },
    "mistral": {
        "label": "Mistral AI",
        "env_key": "MISTRAL_API_KEY",
        "default_model": "mistral-large-latest",
        "key_prefix": "",
        "get_key_url": "https://console.mistral.ai/api-keys",
        "icon": "&#127756;",
    },
}


def get_env_keys():
    """Return dict of provider -> API key from environment variables."""
    return {p: os.environ.get(cfg["env_key"], "") for p, cfg in PROVIDERS.items()}


def is_online(timeout=3):
    if not REQUESTS_OK:
        return False
    try:
        req_lib.get("https://8.8.8.8", timeout=timeout)
        return True
    except Exception:
        return False


def sanitise_key(key):
    """Strip whitespace and non-printable chars. Return '' if too short."""
    if not key or not isinstance(key, str):
        return ""
    key = key.strip()
    if len(key) < 10 or len(key) > 512:
        return ""
    return "".join(c for c in key if 0x20 <= ord(c) <= 0x7E)


def call_ai(provider, api_key, prompt, system_prompt=None, max_tokens=2500, timeout=90):
    """
    Unified entry. Returns (text, "live_ai") on success, (None, error_code) on failure.
    Never raises — all exceptions caught and returned as error strings.
    """
    provider = (provider or "").lower().strip()
    if provider not in PROVIDERS:
        return None, f"unknown_provider"
    api_key = sanitise_key(api_key)
    if not api_key:
        return None, "no_api_key"
    if not REQUESTS_OK:
        return None, "requests_not_installed"
    if not is_online():
        return None, "offline"
    try:
        if provider == "anthropic":
            return _call_anthropic(api_key, prompt, system_prompt, max_tokens, timeout)
        elif provider == "openai":
            return _call_openai(api_key, prompt, system_prompt, max_tokens, timeout)
        elif provider == "gemini":
            return _call_gemini(api_key, prompt, system_prompt, max_tokens, timeout)
        elif provider == "grok":
            return _call_grok(api_key, prompt, system_prompt, max_tokens, timeout)
        elif provider == "deepseek":
            return _call_deepseek(api_key, prompt, system_prompt, max_tokens, timeout)
        elif provider == "mistral":
            return _call_mistral(api_key, prompt, system_prompt, max_tokens, timeout)
    except Exception as e:
        # Never expose key in error
        err = str(e).replace(api_key, "[KEY]") if api_key in str(e) else str(e)
        return None, f"exception: {err[:200]}"
    return None, "unhandled_provider"


def call_multi_ai(provider_key_pairs, prompt, system_prompt=None, max_tokens=2500, timeout=90):
    """
    Ambiguity Resolver: call multiple providers in parallel, return all responses.
    provider_key_pairs: list of (provider_name, api_key)
    Returns: list of {provider, label, text, error, success}
    """
    import threading
    results = []
    lock = threading.Lock()

    def _call_one(provider, api_key):
        text, mode = call_ai(provider, api_key, prompt, system_prompt, max_tokens, timeout)
        with lock:
            results.append({
                "provider": provider,
                "label": PROVIDERS.get(provider, {}).get("label", provider),
                "icon": PROVIDERS.get(provider, {}).get("icon", ""),
                "text": text,
                "mode": mode,
                "success": text is not None,
            })

    threads = []
    for provider, api_key in provider_key_pairs:
        t = threading.Thread(target=_call_one, args=(provider, api_key), daemon=True)
        threads.append(t)
        t.start()
    for t in threads:
        t.join(timeout=timeout + 5)
    return results


# ── Provider implementations ─────────────────────────────────────────────────

def _call_anthropic(api_key, prompt, system_prompt, max_tokens, timeout):
    resp = req_lib.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": PROVIDERS["anthropic"]["default_model"],
            "max_tokens": max_tokens,
            "system": system_prompt or "",
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=timeout,
    )
    if resp.status_code == 200:
        return resp.json()["content"][0]["text"], "live_ai"
    return None, f"anthropic_http_{resp.status_code}"


def _call_openai(api_key, prompt, system_prompt, max_tokens, timeout):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    resp = req_lib.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": PROVIDERS["openai"]["default_model"], "max_tokens": max_tokens, "messages": messages},
        timeout=timeout,
    )
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"], "live_ai"
    return None, f"openai_http_{resp.status_code}"


def _call_gemini(api_key, prompt, system_prompt, max_tokens, timeout):
    model = PROVIDERS["gemini"]["default_model"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    if system_prompt:
        body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    resp = req_lib.post(url, headers={"Content-Type": "application/json"}, json=body, timeout=timeout)
    if resp.status_code == 200:
        try:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"], "live_ai"
        except (KeyError, IndexError):
            return None, "gemini_no_content"
    return None, f"gemini_http_{resp.status_code}"


def _call_grok(api_key, prompt, system_prompt, max_tokens, timeout):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    resp = req_lib.post(
        "https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": PROVIDERS["grok"]["default_model"], "max_tokens": max_tokens, "messages": messages},
        timeout=timeout,
    )
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"], "live_ai"
    return None, f"grok_http_{resp.status_code}"


def _call_deepseek(api_key, prompt, system_prompt, max_tokens, timeout):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    resp = req_lib.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": PROVIDERS["deepseek"]["default_model"], "max_tokens": max_tokens, "messages": messages},
        timeout=timeout,
    )
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"], "live_ai"
    return None, f"deepseek_http_{resp.status_code}"


def _call_mistral(api_key, prompt, system_prompt, max_tokens, timeout):
    """Mistral AI — official API at api.mistral.ai"""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    resp = req_lib.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "model": PROVIDERS["mistral"]["default_model"],
            "max_tokens": max_tokens,
            "messages": messages,
            "safe_prompt": False,
        },
        timeout=timeout,
    )
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"], "live_ai"
    return None, f"mistral_http_{resp.status_code}"
