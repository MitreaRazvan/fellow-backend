from dotenv import load_dotenv
import os

load_dotenv()

PORT = int(os.getenv("PORT", 8000))
DATABASE_URL = os.getenv("DATABASE_URL", "luma.db")

# ── LLM provider ─────────────────────────────────────────────────────────────
# Provider-agnostic: any OpenAI-compatible /chat/completions endpoint works.
# Switch providers from .env alone — no code change.
#
#   Groq (fast, but only 8K tokens/min on the free tier):
#     LLM_BASE_URL=https://api.groq.com/openai/v1
#     LLM_MODEL=qwen/qwen3.8-27b
#     LLM_REASONING_EFFORT=none
#
#   Google Gemini (1M tokens/min free — OpenAI-compatible layer):
#     LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
#     LLM_MODEL=gemini-3.7-flash
#     LLM_API_KEY=<key from aistudio.google.com>
#     LLM_REASONING_EFFORT=            (leave empty — Gemini rejects the field)
#
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen/qwen3.8-27b")

# Falls back to GROQ_API_KEY so existing .env files keep working.
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY", "")

# Only some models accept this field. Empty string == omit it entirely, which
# is required for Gemini (it 400s on an unknown field).
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "none")

CHAT_URL = f"{LLM_BASE_URL}/chat/completions"


def llm_payload(**kwargs) -> dict:
    """Build a request body with the configured model, adding reasoning_effort
    only when the provider supports it."""
    body = {"model": LLM_MODEL, **kwargs}
    if LLM_REASONING_EFFORT:
        body["reasoning_effort"] = LLM_REASONING_EFFORT
    return body


def llm_headers() -> dict:
    return {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}


# Back-compat aliases (older imports)
GROQ_API_KEY = LLM_API_KEY
GROQ_MODEL = LLM_MODEL
GROQ_REASONING_EFFORT = LLM_REASONING_EFFORT
