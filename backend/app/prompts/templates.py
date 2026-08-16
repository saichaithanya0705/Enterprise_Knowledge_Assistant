"""Centralized prompt templates - never inline giant prompt strings in routes."""

SYSTEM_INSTRUCTIONS = """You are the Enterprise Knowledge Assistant, an internal helper that answers \
employee questions about HR, IT, and company policy using ONLY the provided context.

Rules:
- Answer strictly using the context below. Do not use outside knowledge.
- If the context does not contain the answer, say so clearly and suggest who to contact \
(e.g. HR or IT) instead of guessing.
- Never invent policy numbers, dates, or amounts that are not in the context.
- Cite sources inline using the bracket numbers shown in the context, e.g. [1].
- Keep answers concise and directly useful to an employee.
"""

NO_CONTEXT_FALLBACK = (
    "I couldn't find anything in the knowledge base that answers this. "
    "Try rephrasing, or check with HR/IT directly."
)

# Debug traces must remain useful without duplicating sensitive conversation
# history or allowing prompt contents to grow without bound in storage.
PROMPT_PREVIEW_MAX_CHARS = 2_000


def build_chat_messages(context: str, question: str, history: list[dict] | None = None) -> list[dict]:
    """
    Assemble the final message list: system instructions + retrieved context
    + prior conversation turns + the current question.
    """
    messages = [{"role": "system", "content": SYSTEM_INSTRUCTIONS}]

    for turn in (history or [])[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    user_content = f"Context:\n{context}\n\nQuestion: {question}" if context else f"Question: {question}"
    messages.append({"role": "user", "content": user_content})
    return messages


def _clip_preview(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    if max_chars <= 1:
        return text[:max_chars]
    return text[: max_chars - 1] + "…"


def build_prompt_preview(messages: list[dict], *, context: str, question: str) -> str:
    """Render a bounded preview from structured values, redacting history."""
    if not messages:
        return ""

    system_content = str(messages[0].get("content", ""))
    prior_messages = messages[1:-1]

    system_text = _clip_preview(system_content, 500)
    question_text = _clip_preview(question, 400)
    history_marker = f"[{len(prior_messages)} prior conversation messages omitted]"
    prefix = f"system: {system_text}\n\nhistory: {history_marker}\n\nuser context: "
    suffix = f"\n\nuser question: {question_text}"
    context_budget = max(0, PROMPT_PREVIEW_MAX_CHARS - len(prefix) - len(suffix))
    context_preview = _clip_preview(context, context_budget)
    return prefix + context_preview + suffix
