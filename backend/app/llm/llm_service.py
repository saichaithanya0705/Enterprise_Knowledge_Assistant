"""
Dedicated LLM service - the only place that selects chat providers for answer
generation. Routes never call provider clients directly.

Provider order is Key Gateway, NVIDIA chat, then a transparent extractive
answer built from retrieved context. Every generated answer must cite a valid
context source before it can be persisted.
"""
import logging
import re

import httpx

from app.llm.gateway_client import gateway_client, GatewayError
from app.llm.nvidia_client import nvidia_client, NvidiaApiError
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


def _has_in_range_context_citation(answer: str, context: str) -> bool:
    context_ids = {
        int(match.group(1))
        for match in re.finditer(r"(?m)^\[(\d+)\]\s", context)
    }
    answer_ids = {int(match.group(1)) for match in re.finditer(r"\[(\d+)\]", answer)}
    return bool(context_ids & answer_ids)


async def generate_answer(
    context: str,
    question: str,
    history: list[dict] | None = None,
    prepared_messages: list[dict] | None = None,
) -> tuple[str, str]:
    """Returns (answer_text, backend_used)."""
    if not context:
        return NO_CONTEXT_FALLBACK, "local_fallback"

    messages = (
        prepared_messages
        if prepared_messages is not None
        else build_chat_messages(context, question, history)
    )

    if gateway_client.configured:
        try:
            answer = await gateway_client.chat_completion(messages)
            if not isinstance(answer, str) or not _has_in_range_context_citation(answer, context):
                raise GatewayError("Key Gateway answer was not grounded with a valid context citation")
            return answer.strip(), "key_gateway"
        except (GatewayError, httpx.HTTPError) as e:
            logger.warning("Key Gateway call failed; trying NVIDIA chat fallback: %s", e)

    if nvidia_client.configured:
        try:
            answer = await nvidia_client.chat_completion(messages)
            if not isinstance(answer, str) or not _has_in_range_context_citation(answer, context):
                raise NvidiaApiError("NVIDIA chat answer was not grounded with a valid context citation")
            return answer.strip(), "nvidia_chat"
        except (NvidiaApiError, httpx.HTTPError) as e:
            logger.warning("NVIDIA chat fallback failed; using extractive answer: %s", e)

    return _extractive_fallback(context, question), "local_fallback"
