"""
LLM integration - generate filter params from natural language descriptions.
"""

import json
from typing import Optional

import httpx

from .types import FilterParams, MODELS


DEFAULT_MODEL = "openrouter/openai/gpt-oss-20b"
LLM_BASE_URL = "http://prism:8080/openai/v1"


SYSTEM_PROMPT = """You are a color grading expert for image filters. Given a description 
of a desired photo look, respond with ONLY valid JSON matching this schema:

{"contrast": float, "brightness": float, "saturation": float, 
 "fade": float, "grain": float, "temperature": float, 
 "tint": {"r": float, "g": float, "b": float}, "vignette": float,
 "highlights": float, "shadows": float}

Constraints:
- contrast, saturation: 0.5 to 1.5 (default 1.0)
- brightness: -0.2 to 0.2 (default 0.0)
- fade, grain, vignette: 0.0 to 0.5 (default 0.0)
- temperature: -0.3 to 0.3 (default 0.0)
- tint RGB offsets: -0.15 to 0.15 each (default 0.0)
- highlights, shadows: -0.2 to 0.2 (default 0.0)

Use default 1.0/0.0 values where not specified. Start conservative.
Respond with ONLY valid JSON, no explanation, no markdown."""

USER_PROMPT_TEMPLATE = """Create filter parameters for: "{description}"

Current filter state (base your adjustments on this if relevant): {current_params}

Respond with JSON only."""


def generate_from_prompt(
    prompt: str,
    current_params: Optional[FilterParams] = None,
    model: str = DEFAULT_MODEL,
    base_url: str = LLM_BASE_URL,
    timeout: float = 30.0,
) -> FilterParams:
    """
    Call LLM with a description, return FilterParams.
    """
    # Map old model keys to full OpenRouter paths if needed
    if model in MODELS:
        model = MODELS[model]
    elif model == "openai/gpt-4o-mini":
        model = "openrouter/openai/gpt-4o-mini"
    elif model == "groq/openai/gpt-oss-20b":
        model = "openrouter/openai/gpt-oss-20b"

    url = f"{base_url}/chat/completions"

    params_str = json.dumps(current_params or {}, indent=2)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": USER_PROMPT_TEMPLATE.format(
                description=prompt, current_params=params_str
            ),
        },
    ]

    body = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500,
    }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=body)
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]

        parsed = json.loads(content)

        result: FilterParams = {}
        for key, value in parsed.items():
            if value is not None:
                result[key] = value

        return result


def generate_with_fallback(
    prompt: str,
    models: list[str] | None = None,
    base_url: str = LLM_BASE_URL,
) -> FilterParams:
    """
    Try multiple models in order, falling back on failure.

    Args:
        prompt: Description of desired look
        models: List of models to try (default: [gpt-oss-20b, gpt-oss-120b])
        base_url: LLM gateway URL

    Returns:
        FilterParams from first successful model
    """
    if models is None:
        models = [
            "groq/openai/gpt-oss-20b",
            "groq/openai/gpt-oss-120b",
        ]

    last_error: Exception | None = None

    for model in models:
        try:
            return generate_from_prompt(prompt, model=model, base_url=base_url)
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All models failed. Last error: {last_error}") from last_error
