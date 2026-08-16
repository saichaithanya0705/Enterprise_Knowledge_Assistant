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
