"""
Vision-guided filter generation using Gemma 4.
Iteratively refines filter parameters by seeing the image.
"""

import base64
import io
import json
import logging
from typing import Optional

import httpx
from PIL import Image

from .types import FilterParams, merge_with_defaults

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "openrouter/google/gemini-3-flash-preview"
VISION_BASE_URL = "http://prism:8089/v1"


def img_to_base64(img: Image.Image, format: str = "PNG") -> str:
    """Convert PIL Image to base64 string."""
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def img_from_base64(b64: str) -> Image.Image:
    """Load PIL Image from base64 string."""
    img_bytes = base64.b64decode(b64)
    return Image.open(io.BytesIO(img_bytes)).convert("RGB")


VISION_SYSTEM_PROMPT = """You are an expert colorist and photo retoucher. Your job is to analyze images
and suggest filter parameters to improve them.

You must respond with valid JSON matching this schema:
{"contrast": float, "brightness": float, "saturation": float, "vibrance": float,
 "fade": float, "grain": float, "temperature": float, "dehaze": float,
 "clarity": float, "texture": float, "sharpen": float,
 "tint": {"r": float, "g": float, "b": float}, "vignette": float,
 "highlights": float, "shadows": float}

Parameter guidelines:
- contrast, saturation: 0.5-1.5 (1.0 = no change)
- vibrance: -0.5 to 1.0
- brightness, highlights, shadows: -0.2 to 0.2
- fade, grain, vignette: 0.0-0.5
- temperature: -0.3 to 0.3
- tint RGB: -0.15 to 0.15
- dehaze, clarity, texture, sharpen: 0.0 to 1.0

Respond with ONLY valid JSON, no explanation, no markdown."""


VISION_USER_TEMPLATE = """Analyze this image and suggest filter parameters that will improve it.

Current filter state: {current_params}

{focus_instruction}

Respond with JSON only."""


FOCUS_INSTRUCTIONS = {
    "initial": "Provide initial filter parameters to enhance this image. Consider composition, lighting, and mood.",
    "none": "Analyze the image and provide a balanced enhancement. Do not lean too far into any specific style unless the image clearly demands it.",
    "boost_contrast": "The image looks flat. Increase contrast, saturation, and clarity.",
    "warmer": "The image feels too cool/cold. Add warmth via temperature and tint.",
    "cooler": "The image feels too warm. Cool it down.",
    "fade": "Add a subtle fade/grain effect for a vintage look.",
    "pop": "Make colors more vibrant (vibrance), boost clarity and dehaze.",
    "moody": "Reduce brightness, add vignette, push shadows.",
    "glint": "Apply a signature high-contrast but faded look. Lower highlights, boost shadows, and add significant grain/fade for a raw cinematic feel.",
    "detailed": "Enhance fine details with texture and sharpen while keeping colors balanced.",
}


def generate_vision_params(
    image: Image.Image,
    current_params: Optional[FilterParams] = None,
    focus: str = "initial",
    user_prompt: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    base_url: str = VISION_BASE_URL,
    timeout: float = 120.0,
) -> FilterParams:
    """
    Call Gemma 4 vision model to suggest filter improvements.
    """
    url = f"{base_url}/chat/completions"
    image_b64 = img_to_base64(image, "PNG")

    if current_params:
        params_str = json.dumps(current_params, indent=2)
    else:
        params_str = "{}"

    focus_key = focus if focus in FOCUS_INSTRUCTIONS else "initial"
    focus_instruction = (
        user_prompt if user_prompt else FOCUS_INSTRUCTIONS.get(focus_key)
    )

    messages = [
        {"role": "system", "content": VISION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": VISION_USER_TEMPLATE.format(
                        current_params=params_str,
                        focus_instruction=focus_instruction,
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                },
            ],
        },
    ]

    body = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1000,
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=body)
            response.raise_for_status()
            data = response.json()

            # SAFE SUBSCRIPTING
            choices = data.get("choices", [])
            if not choices:
                logger.error(f"Vision model returned no choices: {data}")
                return {}

            content = choices[0].get("message", {}).get("content", "")
            if not content:
                logger.error(f"Vision model returned empty content: {data}")
                return {}

            # Robust JSON parsing
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            result: FilterParams = {}
            for key, value in parsed.items():
                if value is not None:
                    result[key] = value
            return result

    except Exception as e:
        logger.error(f"Vision Gateway Error: {type(e).__name__}: {str(e)}")
        return {}


def iterative_refine(
    image: Image.Image,
    max_rounds: int = 3,
    focus: str = "initial",
    user_prompt: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    base_url: str = VISION_BASE_URL,
    timeout: float = 60.0,
) -> tuple[FilterParams, list[FilterParams]]:
    """
    Run iterative refinement with Gemma 4 vision.
    """
    current_params: FilterParams = {}
    history: list[FilterParams] = []

    for round_num in range(max_rounds):
        logger.info(f"Starting refinement round {round_num + 1}/{max_rounds}")
        is_last = round_num == max_rounds - 1
        this_focus = focus if is_last else "initial"
        this_prompt = user_prompt if is_last else None

        try:
            new_params = generate_vision_params(
                image,
                current_params=current_params if round_num > 0 else None,
                focus=this_focus,
                user_prompt=this_prompt,
                model=model,
                base_url=base_url,
                timeout=timeout,
            )
            if not new_params:
                logger.warning(
                    f"Round {round_num + 1} failed, using last known good params"
                )
                break

            logger.info(f"Round {round_num + 1} params: {new_params}")
            current_params = merge_with_defaults(new_params)
            history.append(current_params.copy())
        except Exception as e:
            logger.error(f"Refinement round {round_num + 1} crashed: {e}")
            break

    return current_params, history


def auto_fix(
    image: Image.Image,
    max_rounds: int = 3,
    focus: str = "pop",
    user_prompt: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    base_url: str = VISION_BASE_URL,
    timeout: float = 60.0,
) -> FilterParams:
    """
    One-liner: analyze image, generate filter, apply it.
    """
    params, _ = iterative_refine(
        image,
        max_rounds=max_rounds,
        focus=focus,
        user_prompt=user_prompt,
        model=model,
        base_url=base_url,
        timeout=timeout,
    )
    return params
