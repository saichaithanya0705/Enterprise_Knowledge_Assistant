"""
Query improvement: expand common workplace abbreviations and trim filler
before retrieval. Uses the Key Gateway chat model for rewriting when
configured; otherwise falls back to a lightweight rule-based expansion so
retrieval still benefits even in local-fallback mode.
"""
import httpx

from app.llm.gateway_client import gateway_client, GatewayError

_ABBREVIATIONS = {
    "pto": "paid time off",
    "wfh": "work from home",
    "hr": "human resources",
    "2fa": "two-factor authentication",
    "reimb": "reimbursement",
}
_MAX_REWRITTEN_QUERY_LENGTH = 1000
# Note: "it" (IT department) is deliberately excluded - it collides with the
# common pronoun "it" and would corrupt most everyday questions.


def _rule_based_expand(query: str) -> str:
    words = query.split()
    expanded = []
    for w in words:
        key = w.strip(".,?!").lower()
        expanded.append(_ABBREVIATIONS.get(key, w))
    result = " ".join(expanded)
    return result if result.lower() != query.lower() else query


async def improve_query(query: str) -> str:
    query = query.strip()
    if not query:
        return query

    if gateway_client.configured:
        try:
            rewritten = await gateway_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Rewrite the user's question into a clearer, self-contained search "
                            "query for a company knowledge base. Keep it short. Do not answer it. "
                            "Return only the rewritten query, nothing else."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                temperature=0.0,
            )
            if not isinstance(rewritten, str):
                raise GatewayError("Key Gateway returned a non-string query rewrite")
            rewritten = rewritten.strip().strip('"').strip()
            if len(rewritten) > _MAX_REWRITTEN_QUERY_LENGTH:
                raise GatewayError("Key Gateway returned an oversized query rewrite")
            return rewritten or query
        except (GatewayError, httpx.HTTPError):
            pass

    return _rule_based_expand(query)
