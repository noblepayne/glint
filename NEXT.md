# NEXT.md - Glint Project Status & Handoff

## Current State
- **Rebranding Complete**: Project is now **Glint v0.2.0**.
- **Functional Core**: `glint/core.py` and `glint/vision.py` are robust.
- **Modern AI**: Switched to **prism** proxy with **Gemini 3 Flash** as default for vision and **GPT-OSS 20B** for text (April 2026 stack).
- **Git Cleaned**: `venv/` has been removed from git tracking and added to `.gitignore`.
- **UI State**: URL Query String synchronization is active for filters, parameters, and model selections.
- **Super Response**: Manual/Auto apply toggle implemented with debouncing and glowing dirty-state feedback.

## Infrastructure
- **Nix**: `flake.nix` is configured to build the `glint` package including static assets.
- **Service**: `glint/server.py` handles the FastAPI backend.

## Tasks Completed
- [x] **Verify Prism Connectivity**: Vision and LLM modules now use the internal proxy.
- [x] **Super Response Mode**: Implemented toggle, keyboard shortcuts, and state-aware "Apply" button.
- [x] **Model Refresh**: Updated dropdowns to feature 2026 high-performance models.
- [x] **Nix Build Verification**: Verified static assets are correctly bundled.

## Immediate Tasks for Next Session
1. **Visual Polish**: Consider adding a histogram or waveform view for the filtered image.
2. **Preset Management**: Allow users to delete or rename saved presets directly from the UI.

## Architectural Mandates (from AGENTS.md)
- **URL is the Source of Truth**.
- **Functional Integrity**: Keep core logic pure.
- **Boundary Defense**: Defensive parsing for LLM outputs.
