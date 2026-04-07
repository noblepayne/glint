# Glint

Traditional image filtering meets iterative vision-guided styling. **Glint** is a professional-grade image processing pipeline that combines pure functional color science with iterative AI refinement.

## Key Features

*   **Iterative Vision Loops**: Uses Gemini/Gemma to analyze photos and calculate optimal filter parameters over discrete refinement rounds. It sees the image, evaluates the histogram, and adjusts.
*   **Prompt-to-Filter**: Describe a look (e.g., "70s moody film grain") and have an LLM derive the underlying color science.
*   **Functional Core**: Pure image transformations built on NumPy and PIL—deterministic, testable, and intentionally side-effect free.
*   **The URL is the Source of Truth**: Every slider move and AI suggestion is encoded in the query string. Deep links work. Browser history works. No "state bleeding."
*   **Universal Presets**: Save combinations of AI and manual tweaks as persistent presets or export as standard `.cube` 3D LUTs for Resolve or Premiere.
*   **Smart Portability**: Download your look as a `.json` file and share it. Drag and drop any `.json` preset onto the workbench to instantly apply the look.
*   **Advanced LUT Import**: Directly apply professional 3D LUTs (S-Log3 supported) via the advanced import accordion.
*   **Pragmatic UX**: A minimalist Pico CSS interface with clipboard support and a "Super Response" live-preview toggle.

## Quick Start (Nix)

Glint is designed for modern development with [Nix Flakes](https://nixos.wiki/wiki/Flakes).

```bash
# Enter the developer shell
nix develop

# Start the Web UI
nix run . -- serve

# List available filters via CLI
nix run . -- list

# AI Auto-fix an image via CLI
nix run . -- auto-fix input.jpg output.png --rounds 3 --focus pop
```

## CLI Usage

*   `glint list`: List all built-in and custom filters.
*   `glint apply <filter> <input> -o <output>`: Apply a preset to an image.
*   `glint generate "<prompt>"`: Create a new filter definition from a description.
*   `glint export <filter> -o <output>.cube`: Export a look for use in professional editing software.
*   `glint serve`: Launch the interactive visual workbench.

## Architecture: Functional Core, Imperative Shell

Glint follows a strict boundary between logic and IO:

1.  **Functional Core (`core.py`)**: Pure functions that transform images. No side effects.
2.  **Calculations (`pipeline.py`)**: The "brain" for merging, blending, and validating parameter sets.
3.  **Imperative Shell (`server.py`, `cli.py`)**: Handles the outside world—FastAPI, local file I/O, and calls to the vision gateway via the `prism` proxy.

## Development & Testing

Stability is prioritized over clever abstractions.

```bash
# Run the test suite
pytest

# Lint and Format
ruff check .
ruff format .
```

## License

MIT
