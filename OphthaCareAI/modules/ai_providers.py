"""
Multi-Provider AI Module
=========================
Supports 5 AI providers with a unified interface:
- Anthropic (Claude)
- OpenAI (ChatGPT/GPT-4o)
- Google (Gemini)
- xAI (Grok)
- DeepSeek

Each provider is called with the same prompt/system_prompt interface
and returns (text, mode) where mode is "live_ai" or an error string.
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
    },
    "openai": {
        "label": "ChatGPT (OpenAI)",
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
        "key_prefix": "sk-",
        "get_key_url": "https://platform.openai.com/api-keys",
    },
    "gemini": {
        "label": "Gemini (Google)",
        "env_key": "GEMINI_API_KEY",
        "default_model": "gemini-2.0-flash",
        "key_prefix": "",
        "get_key_url": "https://aistudio.google.com/apikey",
    },
    "grok": {
        "label": "Grok (xAI)",
        "env_key": "GROK_API_KEY",
        "default_model": "grok-2-latest",
        "key_prefix": "xai-",
        "get_key_url": "https://console.x.ai",
    },
    "deepseek": {
        "label": "DeepSeek",
        "env_key": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
        "key_prefix": "sk-",
        "get_key_url": "https://platform.deepseek.com/api_keys",
    },
}


def get_env_keys():
    """Return dict of provider -> API key from environment variables (server-side default keys)."""
    return {p: os.environ.get(cfg["env_key"], "") for p, cfg in PROVIDERS.items()}


def is_online(timeout=3):
    if not REQUESTS_OK:
        return False
    try:
        req_lib.get("https://8.8.8.8", timeout=timeout)
        return True
    except Exception:
        return False


def call_ai(provider, api_key, prompt, system_prompt=None, max_tokens=2500, timeout=90):
    """
    Unified entry point. provider must be one of PROVIDERS keys.
    Returns (text_or_None, mode_string)
    mode_string is "live_ai" on success, otherwise an error/status code.
    """
    if provider not in PROVIDERS:
        return None, f"unknown_provider_{provider}"
    if not api_key or not REQUESTS_OK:
        return None, "no_api_key"
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
    except Exception as e:
        return None, f"exception: {e}"

    return None, "unhandled_provider"


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
        data = resp.json()
        return data["content"][0]["text"], "live_ai"
    return None, f"anthropic_error_{resp.status_code}: {resp.text[:200]}"


def _call_openai(api_key, prompt, system_prompt, max_tokens, timeout):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    resp = req_lib.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": PROVIDERS["openai"]["default_model"],
            "max_tokens": max_tokens,
            "messages": messages,
        },
        timeout=timeout,
    )
    if resp.status_code == 200:
        data = resp.json()
        return data["choices"][0]["message"]["content"], "live_ai"
    return None, f"openai_error_{resp.status_code}: {resp.text[:200]}"


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
        data = resp.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return text, "live_ai"
        except (KeyError, IndexError):
            return None, "gemini_error_no_content"
    return None, f"gemini_error_{resp.status_code}: {resp.text[:200]}"


def _call_grok(api_key, prompt, system_prompt, max_tokens, timeout):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    resp = req_lib.post(
        "https://api.x.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": PROVIDERS["grok"]["default_model"],
            "max_tokens": max_tokens,
            "messages": messages,
        },
        timeout=timeout,
    )
    if resp.status_code == 200:
        data = resp.json()
        return data["choices"][0]["message"]["content"], "live_ai"
    return None, f"grok_error_{resp.status_code}: {resp.text[:200]}"


def _call_deepseek(api_key, prompt, system_prompt, max_tokens, timeout):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    resp = req_lib.post(
        "https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": PROVIDERS["deepseek"]["default_model"],
            "max_tokens": max_tokens,
            "messages": messages,
        },
        timeout=timeout,
    )
    if resp.status_code == 200:
        data = resp.json()
        return data["choices"][0]["message"]["content"], "live_ai"
    return None, f"deepseek_error_{resp.status_code}: {resp.text[:200]}"
