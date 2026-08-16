"""
Dedicated LLM service - the only place that talks to the Key Gateway for
answer generation. Routes never call the gateway client directly.

When the Key Gateway isn't configured yet, falls back to a transparent
extractive answer built from the retrieved context, so the app is fully
demoable before real credentials are wired in.
"""
import logging

import httpx

from app.llm.gateway_client import gateway_client, GatewayError
from app.prompts.templates import build_chat_messages, NO_CONTEXT_FALLBACK

logger = logging.getLogger(__name__)


def _extractive_fallback(context: str, question: str) -> str:
    if not context:
        return NO_CONTEXT_FALLBACK
    return (
        "[Local fallback mode - no Key Gateway configured yet, so this is an extractive "
        "answer built directly from the most relevant passage rather than an LLM-generated one.]\n\n"
        + context.split("\n\n---\n\n")[0]
    )


async def generate_answer(context: str, question: str, history: list[dict] | None = None) -> tuple[str, str]:
    """Returns (answer_text, backend_used)."""
    if gateway_client.configured:
        try:
            messages = build_chat_messages(context, question, history)
            answer = await gateway_client.chat_completion(messages)
            return answer.strip(), "key_gateway"
        except (GatewayError, httpx.HTTPError) as e:
            # Belt-and-suspenders: gateway_client should already wrap HTTP
            # failures as GatewayError, but a raw transport-level error
            # (network drop, timeout after retries) must not crash the whole
            # chat request either - always fall back to the extractive answer.
            logger.warning("Key Gateway call failed, falling back to extractive answer: %s", e)
            return _extractive_fallback(context, question), "local_fallback"

    return _extractive_fallback(context, question), "local_fallback"