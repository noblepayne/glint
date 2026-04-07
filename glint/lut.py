"""
Generate and load .cube LUT files following Adobe/Iridash standard conventions.
"""

from pathlib import Path

import numpy as np

from .types import FilterParams
from .pipeline import build_color_pipeline, apply_pipeline


def generate_cube(
    params: FilterParams, size: int = 33, title: str = "glint_filter"
) -> np.ndarray:
    """
    Generate a 3D LUT as numpy array.
    Standard ordering: Red slowest (outermost), Blue fastest (innermost).
    """
    # Create coordinate grid: 0.0 to 1.0
    indices = np.linspace(0, 1, size)
    # meshgrid with indexing="ij" gives [r, g, b] order
    r, g, b = np.meshgrid(indices, indices, indices, indexing="ij")

    # Stack into (size, size, size, 3) where last dim is RGB
    rgb = np.stack([r, g, b], axis=-1)

    # Apply global color pipeline
    pipeline = build_color_pipeline(params)
    transformed = apply_pipeline(rgb, pipeline)

    # Flatten to list of lines for .cube format
    return transformed.reshape(-1, 3)


def save_cube(
    params: FilterParams, output_path: Path, size: int = 33, title: str | None = None
) -> Path:
    """
    Generate and save a .cube file.
    """
    if title is None:
        title = params.get("name", "glint_filter")

    lut_data = generate_cube(params, size, title)

    with open(output_path, "w") as f:
        f.write(f'TITLE "{title}"\n')
        f.write(f"LUT_3D_SIZE {size}\n")
        f.write("DOMAIN_MIN 0.0 0.0 0.0\n")
        f.write("DOMAIN_MAX 1.0 1.0 1.0\n\n")

        for rgb in lut_data:
            f.write(f"{rgb[0]:.6f} {rgb[1]:.6f} {rgb[2]:.6f}\n")

    return output_path


def load_cube(path: Path) -> tuple[np.ndarray, int, str]:
    """
    Load a .cube file and return (data, size, title).
    Ensures standard Red-slowest, Blue-fastest ordering.
    """
    data = []
    size = 0
    title = "unknown"

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("LUT_3D_SIZE"):
                size = int(line.split()[-1])
                continue
            if line.startswith("TITLE"):
                title = line.replace("TITLE", "").strip().strip('"')
                continue
            if line.startswith("DOMAIN"):
                continue

            parts = line.split()
            if len(parts) == 3:
                try:
                    data.append([float(x) for x in parts])
                except ValueError:
                    continue

    arr = np.array(data)
    if size == 0:
        size = int(round(len(arr) ** (1 / 3)))

    # Return as (size, size, size, 3) for trilinear interpolation
    return arr.reshape(size, size, size, 3), size, title
