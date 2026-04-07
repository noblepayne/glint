"""
Web server for glint - visual filter preview and experimentation.
"""

import base64
import io
import json
import logging
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Template
from PIL import Image

from . import llm, vision
from .apply import apply_to_image
from .filters import FILTERS, get_filter, list_filters

logger = logging.getLogger(__name__)

app = FastAPI(title="Glint", description="Image filter pipeline with LLM support")

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Store uploaded images temporarily
UPLOAD_DIR = Path("/tmp/glint-uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def img_to_base64(img: Image.Image, format: str = "PNG") -> str:
    """Convert PIL Image to base64 string."""
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def img_to_data_url(img: Image.Image, format: str = "PNG") -> str:
    """Convert PIL Image to data URL."""
    b64 = img_to_base64(img, format)
    mime = f"image/{format.lower()}"
    return f"data:{mime};base64,{b64}"


@app.get("/", response_class=HTMLResponse)
async def index():
    """Main UI page."""
    filters = list_filters()
    # Convert list of tuples to list of lists for JavaScript
    filters_json = [[name, desc] for name, desc in filters]

    index_path = static_dir / "index.html"
    with open(index_path, "r") as f:
        template = Template(f.read())

    return template.render(filters_json=json.dumps(filters_json))


@app.post("/upload")
async def upload(file: UploadFile = File(...)) -> JSONResponse:
    """Handle image upload."""
    contents = await file.read()

    try:
        img = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")

    # Resize for performance if too large
    max_size = 1200
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    image_b64 = img_to_data_url(img, "PNG")

    return JSONResponse({"image": image_b64})


@app.get("/filter/{name}")
async def get_filter_params(name: str) -> JSONResponse:
    """Get filter parameters by name."""
    f = get_filter(name)
    if f is None:
        raise HTTPException(status_code=404, detail=f"Filter '{name}' not found")

    # Return params without description/name for the UI
    result = {}
    for key, value in f.items():
        if key not in ("name", "description"):
            result[key] = value

    return JSONResponse(result)


@app.post("/apply")
async def apply_filter(request: dict) -> JSONResponse:
    """Apply filter to image."""
    image_data = request.get("image")
    params = request.get("params", {})

    if not image_data:
        raise HTTPException(status_code=400, detail="Image is required")

    # Decode base64 image
    try:
        header, b64data = image_data.split(",", 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid image format")

    img_bytes = base64.b64decode(b64data)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

    # Apply filter
    result_img = apply_to_image(img, params)

    # Return as base64
    result_b64 = img_to_data_url(result_img, "PNG")

    return JSONResponse({"image": result_b64})


@app.post("/generate")
async def generate_from_llm(request: dict) -> JSONResponse:
    """Generate filter parameters from LLM."""
    prompt = request.get("prompt", "")
    params = request.get("params", {})  # Get current params from UI
    model = request.get("model", llm.DEFAULT_MODEL)

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    try:
        params = llm.generate_from_prompt(prompt, current_params=params, model=model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")

    return JSONResponse({"params": params})


@app.post("/save-filter")
async def save_filter(request: dict) -> JSONResponse:
    """Save a custom filter."""
    name = request.get("name", "").strip()
    params = request.get("params", {})

    if not name:
        raise HTTPException(status_code=400, detail="Filter name is required")

    if not params:
        raise HTTPException(status_code=400, detail="Filter params are required")

    # Add to FILTERS dict in memory
    filter_id = name.lower().replace(" ", "-")
    FILTERS[filter_id] = {"name": name, "description": "Custom filter", **params}

    # Persist to filters.py
    try:
        filters_file = Path(__file__).parent / "filters.py"
        with open(filters_file, "r") as f:
            lines = f.readlines()

        # Find the end of the FILTERS dict
        end_idx = -1
        for i, line in enumerate(reversed(lines)):
            if "}" in line and i < 5:  # Should be near the end of the dict
                end_idx = len(lines) - 1 - i
                break

        if end_idx != -1:
            # Prepare the new entry
            entry_params = params.copy()
            entry_params["name"] = name
            entry_params["description"] = "Custom filter"
            new_entry = f'    "{filter_id}": {json.dumps(entry_params, indent=8).strip()[:-1]}    }},\n'

            lines.insert(end_idx, new_entry)

            with open(filters_file, "w") as f:
                f.writelines(lines)
    except Exception as e:
        logger.error(f"Failed to persist filter: {e}")
        # We still return success since it's in memory for the current session

    return JSONResponse({"status": "saved", "name": name, "id": filter_id})


@app.post("/export-cube")
async def export_cube(request: dict) -> JSONResponse:
    """Export filter parameters as a .cube LUT file (base64)."""
    params = request.get("params", {})
    if not params:
        raise HTTPException(status_code=400, detail="Params are required")

    from .lut import save_cube
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".cube", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        save_cube(params, tmp_path)
        with open(tmp_path, "rb") as f:
            cube_data = base64.b64encode(f.read()).decode()
        return JSONResponse({"cube": cube_data, "filename": "filter.cube"})
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@app.get("/filters")
async def list_all_filters() -> JSONResponse:
    """List all available filters including custom ones."""
    return JSONResponse({"filters": list_filters()})


@app.post("/vision/auto-fix")
async def vision_auto_fix(request: dict) -> JSONResponse:
    """Apply auto-fix using vision model via prism."""
    image_data = request.get("image")
    max_rounds = request.get("max_rounds", 3)
    focus = request.get("focus", "pop")
    user_prompt = request.get("prompt")
    model = request.get("model")

    if not image_data:
        raise HTTPException(status_code=400, detail="Image is required")

    try:
        header, b64data = image_data.split(",", 1)
        img_bytes = base64.b64decode(b64data)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        params = vision.auto_fix(
            img,
            max_rounds=max_rounds,
            focus=focus,
            user_prompt=user_prompt,
            model=model if model else vision.DEFAULT_MODEL,
        )

        result_img = apply_to_image(img, params)
        result_b64 = img_to_data_url(result_img, "PNG")

        return JSONResponse(
            {
                "params": params,
                "image": result_b64,
            }
        )
    except Exception as e:
        import traceback

        error_detail = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(f"VISION ERROR DEBUG:\n{error_detail}")
        raise HTTPException(status_code=500, detail=f"Vision error: {str(e)}")


@app.post("/vision/refine")
async def vision_refine(request: dict) -> JSONResponse:
    """Run iterative refinement with Gemma 4."""
    image_data = request.get("image")
    max_rounds = request.get("max_rounds", 3)
    focus = request.get("focus", "initial")

    if not image_data:
        raise HTTPException(status_code=400, detail="Image is required")

    try:
        header, b64data = image_data.split(",", 1)
        img_bytes = base64.b64decode(b64data)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        final_params, history = vision.iterative_refine(
            img,
            max_rounds=max_rounds,
            focus=focus,
        )

        result_img = apply_to_image(img, final_params)
        result_b64 = img_to_data_url(result_img, "PNG")

        return JSONResponse(
            {
                "final_params": final_params,
                "history": history,
                "image": result_b64,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
