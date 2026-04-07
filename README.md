# ✨ Glint

Traditional image filtering meets LLM and Vision styling. **Glint** is a professional-grade image processing pipeline that combines pure functional color science with iterative AI refinement.

## 🚀 Key Features

*   **Iterative Vision Loops**: Use Gemma 4 to analyze your photo and automatically calculate optimal filter parameters over 1–5 refinement rounds.
*   **Prompt-to-Filter**: Describe a look (e.g., "70s moody film grain") and have an LLM generate the underlying color science.
*   **Functional Core**: Pure image transformations built on NumPy and PIL—reliable, testable, and fast.
*   **State-in-URL**: Every tweak, slider move, or AI suggestion is encoded in the URL. Share your exact looks with deep links and enjoy full Back/Forward browser support.
*   **Universal Presets**: Save any combination of AI and manual tweaks as a persistent preset or export as a standard `.cube` 3D LUT.
*   **Pro UX**: Minimalist Pico CSS interface with clipboard support (Ctrl+V to paste, Copy to clipboard).

## 🛠 Quick Start (Nix)

Glint is designed for modern development with [Nix Flakes](https://nixos.wiki/wiki/Flakes).

```bash
# Enter the developer shell (includes all Python deps, ruff, black, pytest)
nix develop

# Start the Web UI
nix run . -- serve

# List available filters via CLI
nix run . -- list

# AI Auto-fix an image via CLI
nix run . -- auto-fix input.jpg output.png --rounds 3 --focus pop
```

## 📖 CLI Usage

Glint provides a robust command-line interface for batch processing and experimentation.

*   `glint list`: List all built-in and custom filters.
*   `glint apply <filter> <input> -o <output>`: Apply a preset to an image.
*   `glint generate "<prompt>"`: Create a new filter definition from a description.
*   `glint export <filter> -o <output>.cube`: Export a look for use in professional editing software.
*   `glint serve`: Launch the interactive visual workbench.

## 📐 Architecture: Functional Core, Imperative Shell

Glint follows a strict architectural pattern inspired by Clojure:

1.  **Functional Core (`core.py`)**: Pure functions that take an image and parameters, returning a new image. No side effects, no state.
2.  **Calculations (`pipeline.py`)**: Logic for merging, blending, and validating filter parameters.
3.  **Imperative Shell (`server.py`, `cli.py`)**: Handles the outside world—FastAPI, local file I/O, and calls to the Gemma 4 vision gateway.

## 🧪 Development & Testing

We maintain a high quality bar with over 100+ automated tests covering edge cases, color science accuracy, and API stability.

```bash
# Run the test suite
pytest

# Lint and Format
ruff check .
ruff format .
```

## 📜 License

MIT
