import json
import os
from litellm import acompletion  # type: ignore

# ── Context Window ────────────────────────────────────────────────────────────
# keeps the last 3-5 sentences for context
context_window: list[str] = []
MAX_CONTEXT = 5

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are a teaching assistant explaining a technical video to a learning audience. 
You are provided transcribed sentences from this video. 
Identify pieces of information and explain them in a clear, informational, and educational tone.
As a jargon detection assistant, your job is to identify complex, domain-specific, or technical terms in the text provided that an average person might not understand.

Rules:
- Return ONLY a JSON object, no preamble, no markdown, no explanation
- If no jargon is found, return an empty jargon_terms array
- Keep "explanation" short and clear (1-4 sentences max) — a plain account of
  what's being said. It can carry some depth if that's the natural way to
  explain it, but it doesn't need to strain for insight — that's "insight"'s job.
- Use "insight" for whatever explanation doesn't already cover: the "why" or
  "how" behind it, a comparison to something familiar, a concrete example, or
  a caveat/misconception worth flagging. Reach naturally for whichever fits —
  don't force one that doesn't. If the sentence is purely administrative or
  logistical with nothing genuinely deeper to add, return "insight" as an
  empty string rather than manufacturing something.
- The transcript may contain speech-to-text errors (misspelled or garbled words). If you're confident what a jargon term actually is, do not include the misspelling; report and explain it under its correct standard spelling rather than the garbled transcript version.

Return this exact structure:
{
    "original_text": "the full sentence",
    "explanation": "your plain English explanation of what is being discussed",
    "insight": "the why/how, a comparison, an example, or a caveat — or an empty string if the sentence has nothing deeper to offer",
    "jargon_terms": [
        {
            "term": "the jargon word or phrase",
            "explanation": "plain English explanation",
            "confidence": 0.9
        }
    ]
}
"""


def reset_context() -> None:
    """Clears accumulated context. Call this when the viewer switches to a new
    video, so explanations for the new video aren't influenced by leftover
    sentences from whatever was playing before."""
    context_window.clear()


def _is_configured(key: str | None) -> bool:
    """True if `key` looks like a real credential — not unset, blank/whitespace,
    or an unfilled placeholder value (e.g. "your-openai-key-here")."""
    if key is None:
        return False
    value = key.strip()
    if not value:
        return False
    return "your-" not in value.lower()


def _build_model_chain() -> list[str]:
    """Orders candidate models by which API keys are actually configured in the
    environment, so we never waste a call on a provider we know has no real
    credentials. litellm's `fallbacks=` still handles the "key exists but the
    call fails anyway" case (rate limits, no credits, etc.) for whichever
    providers ARE configured.
    """
    chain: list[str] = []
    if _is_configured(os.getenv("OPENAI_API_KEY")):
        chain.append("gpt-4o-mini")
    if _is_configured(os.getenv("GEMINI_API_KEY")):
        # "gemini-flash-lite-latest" auto-updates like "gemini-flash-latest"
        # (never goes stale), but stays on the Flash-Lite tier. The full Flash
        # tier's free quota is throttled hardest on whichever model is newest —
        # gemini-flash-latest currently resolves to gemini-3.5-flash, which
        # free-tier caps at just 20 requests/day. Flash-Lite gets ~1,000+/day.
        chain.append("gemini/gemini-flash-lite-latest")

    if not chain:
        raise RuntimeError(
            "No LLM API key configured — set OPENAI_API_KEY or GEMINI_API_KEY in .env"
        )
    return chain


async def detect_jargon(sentence: str) -> dict[str, object]:
    """Send a sentence to the LLM and get back detected jargon with explanations."""

    # add sentence to context window
    context_window.append(sentence)
    if len(context_window) > MAX_CONTEXT:
        context_window.pop(0)

    context = " ".join(context_window[:-1])

    user_message = f"""
Context (recent sentences): {context if context else "None"}

Current sentence to analyse: {sentence}
"""

    model_chain = _build_model_chain()

    response = await acompletion(  # type: ignore
        model=model_chain[0],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        fallbacks=model_chain[1:],
    )

    result: dict[str, object] = json.loads(response.choices[0].message.content)  # type: ignore
    return result
