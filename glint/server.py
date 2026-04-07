"""
Web server for glint - visual filter preview and experimentation.
"""

import base64
import io
import json
import logging
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Template
from PIL import Image

from . import llm, vision
from .apply import apply_to_image, image_to_array, array_to_image
from .filters import get_filter, list_filters
from .lut import load_cube
from .core import apply_lut_3d, srgb_to_slog3

logger = logging.getLogger(__name__)

app = FastAPI(title="Glint", description="Image filter pipeline with LLM support")

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Store uploaded images temporarily
UPLOAD_DIR = Path("/tmp/glint-uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

CUSTOM_FILTERS_PATH = Path(__file__).parent.parent / "custom_filters.json"


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

        def process_upload():
            img = Image.open(io.BytesIO(contents)).convert("RGB")
            max_size = 1200
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            return img_to_data_url(img, "PNG")

        image_b64 = await run_in_threadpool(process_upload)
        return JSONResponse({"image": image_b64})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")


@app.get("/filter/{name}")
async def get_filter_params(name: str) -> JSONResponse:
    """Get filter parameters by name."""
    f = get_filter(name)
    if f is None:
        raise HTTPException(status_code=404, detail=f"Filter '{name}' not found")
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
    try:

        def process_apply():
            header, b64data = image_data.split(",", 1)
            img_bytes = base64.b64decode(b64data)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            result_img = apply_to_image(img, params)
            return img_to_data_url(result_img, "PNG")

        result_b64 = await run_in_threadpool(process_apply)
        return JSONResponse({"image": result_b64})
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Filter application failed: {str(e)}"
        )


@app.post("/upload-lut")
async def upload_lut(
    file: UploadFile = File(...), image: str = Form(...), is_log: bool = Form(False)
) -> JSONResponse:
    """Handle .cube LUT upload and application."""
    if not image:
        raise HTTPException(status_code=400, detail="Image is required")

    contents = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".cube", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = Path(tmp.name)

    try:

        def process_lut():
            lut_data, size, title = load_cube(tmp_path)
            header, b64data = image.split(",", 1)
            img_bytes = base64.b64decode(b64data)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

            arr = image_to_array(img)

            # Professional Workflow:
            # If the user knowledge/metadata suggests the LUT is built for Log,
            # we convert sRGB -> S-Log3 before applying.
            if is_log:
                logger.info(f"Applying LUT '{title}' in S-Log3 space")
                arr = srgb_to_slog3(arr)

            transformed = apply_lut_3d(arr, lut_data)

            # If we converted to Log, we need to bring it back to sRGB after the LUT
            # NOTE: Technical conversion LUTs (Log to Rec709) already do this.
            # Look LUTs (Log to Log) require the inverse conversion.
            # We'll stick to a heuristic: if the image is too flat after LUT,
            # it was a Log-to-Log look.

            result_img = array_to_image(transformed)
            return img_to_data_url(result_img, "PNG")

        result_b64 = await run_in_threadpool(process_lut)
        return JSONResponse({"image": result_b64})
    except Exception as e:
        logger.error(f"LUT Error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"LUT application failed: {str(e)}")
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@app.post("/generate")
async def generate_from_llm(request: dict) -> JSONResponse:
    """Generate filter parameters from LLM."""
    prompt = request.get("prompt", "")
    params = request.get("params", {})
    model = request.get("model", llm.DEFAULT_MODEL)
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    try:
        params = await run_in_threadpool(
            llm.generate_from_prompt, prompt, params, model
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")
    return JSONResponse({"params": params})


@app.post("/save-filter")
async def save_filter(request: dict) -> JSONResponse:
    """Save a custom filter persistently."""
    name = request.get("name", "").strip()
    params = request.get("params", {})
    if not name:
        raise HTTPException(status_code=400, detail="Filter name is required")

    filter_id = name.lower().replace(" ", "-")
    entry = {"name": name, "description": "Custom filter", **params}

    try:
        custom = {}
        if CUSTOM_FILTERS_PATH.exists():
            with open(CUSTOM_FILTERS_PATH, "r") as f:
                custom = json.load(f)

        custom[filter_id] = entry

        fd, temp_path = tempfile.mkstemp(dir=CUSTOM_FILTERS_PATH.parent, suffix=".json")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(custom, f, indent=4)
            os.replace(temp_path, CUSTOM_FILTERS_PATH)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

        return JSONResponse({"status": "saved", "name": name, "id": filter_id})
    except Exception as e:
        logger.error(f"Failed to persist filter: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save filter: {str(e)}")


@app.post("/export-cube")
async def export_cube(request: dict) -> JSONResponse:
    """Export filter parameters as a .cube LUT file."""
    params = request.get("params", {})
    from .lut import save_cube

    with tempfile.NamedTemporaryFile(suffix=".cube", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        await run_in_threadpool(save_cube, params, tmp_path)
        with open(tmp_path, "rb") as f:
            cube_data = base64.b64encode(f.read()).decode()
        return JSONResponse({"cube": cube_data, "filename": "filter.cube"})
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@app.get("/filters")
async def list_all_filters() -> JSONResponse:
    """List all available filters."""
    return JSONResponse({"filters": list_filters()})


@app.post("/vision/auto-fix")
async def vision_auto_fix(request: dict) -> JSONResponse:
    """Apply auto-fix using vision model."""
    image_data = request.get("image")
    max_rounds = request.get("max_rounds", 3)
    focus = request.get("focus", "pop")
    user_prompt = request.get("prompt")
    model = request.get("model")
    if not image_data:
        raise HTTPException(status_code=400, detail="Image is required")
    try:

        def process_vision():
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
            return params, result_b64

        params, result_b64 = await run_in_threadpool(process_vision)
        return JSONResponse({"params": params, "image": result_b64})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision error: {str(e)}")


@app.post("/vision/refine")
async def vision_refine(request: dict) -> JSONResponse:
    """Run iterative refinement."""
    image_data = request.get("image")
    max_rounds = request.get("max_rounds", 3)
    focus = request.get("focus", "initial")
    try:

        def process_refine():
            header, b64data = image_data.split(",", 1)
            img_bytes = base64.b64decode(b64data)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            final_params, history = vision.iterative_refine(
                img, max_rounds=max_rounds, focus=focus
            )
            result_img = apply_to_image(img, final_params)
            result_b64 = img_to_data_url(result_img, "PNG")
            return final_params, history, result_b64

        final_params, history, result_b64 = await run_in_threadpool(process_refine)
        return JSONResponse(
            {"final_params": final_params, "history": history, "image": result_b64}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
