import asyncio
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_YORKSHIRE_SYSTEM_PROMPT = """
You are the voice of a Discord bot used by a group of friends to pick games to play together.
You have a warm, funny Yorkshire personality — think friendly local at a pub, not a caricature.
Use Yorkshire dialect naturally but don't overdo it. Phrases like "reyt", "aye", "nay", "nowt",
"summat", "tha knows", "right good", "grand", "by 'eck" are welcome but shouldn't appear in every sentence.
Keep responses short — one or two sentences at most. No bullet points, no markdown formatting,
no emojis unless they feel natural. Never break character.
""".strip()


def _get_model():
    """Initialise the chat model from environment variables."""
    from langchain.chat_models import init_chat_model

    model = os.environ.get("AI_MODEL", "gpt-4o-mini")
    provider = os.environ.get("AI_PROVIDER", "openai")
    temperature = float(os.environ.get("AI_TEMPERATURE", "0.9"))

    return init_chat_model(model=model, model_provider=provider, temperature=temperature)


def _generate_sync(situation: str, extra_context: Optional[str] = None) -> str:
    """Synchronous langchain call — run this via asyncio.to_thread."""
    prompt = f"{_YORKSHIRE_SYSTEM_PROMPT}\n\nSituation: {situation}"
    if extra_context:
        prompt += f"\nContext: {extra_context}"
    prompt += "\n\nRespond in character. One or two sentences only."

    try:
        model = _get_model()
        response = model.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        logger.error(f"AI response failed: {e}")
        return None


async def generate_response(situation: str, extra_context: Optional[str] = None) -> Optional[str]:
    """
    Async wrapper around the langchain call using asyncio.to_thread so it
    doesn't block the Discord event loop. Returns None if the call fails,
    so callers can fall back to a hardcoded string.
    """
    return await asyncio.to_thread(_generate_sync, situation, extra_context)