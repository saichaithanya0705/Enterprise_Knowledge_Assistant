"""Validation helpers shared by OpenAI-compatible chat providers."""


class ChatCompletionContractError(ValueError):
    """Raised when a provider returns a malformed chat-completion payload."""


def extract_chat_content(payload: object, provider: str) -> str:
    if not isinstance(payload, dict):
        raise ChatCompletionContractError(f"{provider} returned a non-object payload")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ChatCompletionContractError(f"{provider} response did not contain choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ChatCompletionContractError(f"{provider} response did not contain a message")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ChatCompletionContractError(f"{provider} response did not contain string content")
    return content
