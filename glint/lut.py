"""
Generate .cube LUT files from FilterParams.
"""

from pathlib import Path

import numpy as np

from .types import FilterParams
from .pipeline import build_pipeline


def generate_cube(
    params: FilterParams, size: int = 33, title: str = "glint_filter"
) -> np.ndarray:
    """
    Generate a 3D LUT as numpy array.

    Args:
        params: Filter parameters
        size: LUT size (e.g., 33 for 33x33x33)
        title: Title for the .cube file

    Returns:
        numpy array of shape (size^3, 3) with values 0-1
    """
    r, g, b = np.mgrid[0:size, 0:size, 0:size] / (size - 1.0)

    rgb = np.stack([r.ravel(), g.ravel(), b.ravel()], axis=1).reshape(
        size, size, size, 3
    )

    from .pipeline import apply_pipeline

    pipeline = build_pipeline(params)

    transformed = apply_pipeline(rgb, pipeline)

    return transformed.reshape(-1, 3)


def save_cube(
    params: FilterParams, output_path: Path, size: int = 33, title: str | None = None
) -> Path:
    """
    Generate and save a .cube file.

    Args:
        params: Filter parameters
        output_path: Path to save .cube file
        size: LUT size
        title: Title (defaults to filter name or 'glint_filter')

    Returns:
        Path to saved file
    """
    if title is None:
        title = params.get("name", params.get("name", "glint_filter"))

    lut = generate_cube(params, size, title)

    with open(output_path, "w") as f:
        f.write(f'TITLE "{title}"\n')
        f.write(f"LUT_3D_SIZE {size}\n")
        f.write("DOMAIN_MIN 0.0 0.0 0.0\n")
        f.write("DOMAIN_MAX 1.0 1.0 1.0\n\n")

        for rgb in lut:
            f.write(f"{rgb[0]:.6f} {rgb[1]:.6f} {rgb[2]:.6f}\n")

    return output_path


def load_cube(path: Path) -> np.ndarray:
    """Load a .cube file and return as numpy array."""
    data = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("LUT_3D_SIZE"):
                continue
            if line.startswith("DOMAIN"):
                continue
            if line.startswith("TITLE"):
                continue

            parts = line.split()
            if len(parts) == 3:
                data.append([float(x) for x in parts])

    return np.array(data)
