import json
from litellm import completion  # type: ignore

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
- Keep explanations short, clear and simple (1-2 sentences max)

Return this exact structure:
{
    "original_text": "the full sentence",
    "explanation": "your plain English explanation of what is being discussed",
    "jargon_terms": [
        {
            "term": "the jargon word or phrase",
            "explanation": "plain English explanation",
            "confidence": 0.9
        }
    ]
}
"""


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

    response = completion(  # type: ignore
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        fallbacks=["gemini/gemini-1.5-flash"],
    )

    result: dict[str, object] = json.loads(response.choices[0].message.content)  # type: ignore
    return result
