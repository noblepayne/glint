# Glint Storage & Persistence Guide

Glint v0.2.0 implements a **Bulletproof Persistence** system designed to work in standard local environments, Docker, and read-only Nix stores.

## 1. Custom Filter Location

Glint uses a prioritized discovery logic to find a writable location for your custom presets:

1.  **Environment Variable**: If `GLINT_PRESETS_PATH` is set, Glint will use that exact file path.
2.  **User Config (Recommended)**: `~/.config/glint/custom_filters.json` (Linux/macOS).
3.  **Fallback**: `/tmp/glint_custom_filters.json` (used if home directory is unwritable).

## 2. Synchronizing Looks

To move your "looks" between machines:
- Copy the `custom_filters.json` file to the same relative location on the new machine.
- Alternatively, use the **"Download JSON"** button in the UI to export a single look and **Drag & Drop** it onto the Glint interface on another machine to import it.

## 3. Session Safety

Glint mirrors all slider states to your browser's `localStorage`.
- **Refresh Protection**: If you accidentally refresh the page, your parameters are restored.
- **Deep Linking**: Parameters are also mirrored in the URL query string. You can share the URL to share the exact look.
