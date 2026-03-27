import json
import time
import litellm  
import config  # type: ignore

SYSTEM_PROMPT = """
You are a teaching assistant explaining a technical video to an audience who would like to learn. 
You are provided transcribed sentences from this video. 
     
Define any jargon or technical terms separately and explain them in context with the main explanation.

Return ONLY a valid JSON object with no markdown, no code blocks, and no additional text. Use exactly this structure:

{
  "original_text": "the transcribed sentence you were given",
  "teaching": {
    "explanation":,,
    "terms": [
      {
        "term": "the jargon term",
        "definition": "plain English definition of the term",
        "type": "jargon"
      }
    ]
  },
  "timestamp": 0
}

If no jargon terms are identified, return an empty array for terms. The timestamp field should be left as 0 — it will be set by the application.
"""

litellm.api_key = config.GEMINI_API_KEY

async def get_teaching_explanation(sentence: str) -> dict: # type: ignore
    """Takes a transcribed sentence and returns a teaching explanation as a dict."""

    response = await litellm.acompletion(  # type: ignore
        model="gemini/gemini-2.0-flash",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": sentence}
        ],
    )

    raw: str = response.choices[0].message.content # type: ignore
    
    try:
        result: dict = json.loads(raw) # type: ignore
    except json.JSONDecodeError:
        result = { # type: ignore
            "original_text": sentence,
            "teaching": {
                "explanation": raw,
                "terms": []
            },
            "timestamp": 0
        }

    result["timestamp"] = int(time.time())
    return result # type: ignore