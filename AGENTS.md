# Development Standards (AGENTS.md)

This project was built following the **"Pro-Dev Agentic Protocols"**. If you are an agent working on this codebase, adhere to these mandates:

## 1. Functional Integrity
*   Keep `glint/core.py` pure. Image transforms must be deterministic and side-effect free.
*   Data is data: Use `TypedDict` for `FilterParams`. Do not introduce complex classes for simple data structures.

## 2. The Machine (State Management)
*   The **URL is the Source of Truth**. Every UI action that modifies the image state must be reflected in the query string.
*   **Identity First**: When switching filters, always reset to the 1.0 identity transform before merging new data to prevent "state bleeding."

## 3. Boundary Defense (AI Safety)
*   **Defense in Depth**: Never assume an LLM or Vision gateway returns valid JSON. Use multi-level `.get()` calls and robust string strippers.
*   **Graceful Degression**: If a vision refinement round fails, return the last known good state. Never crash the shell for a calculation failure.

## 4. Operational Excellence
*   **Nix First**: Always verify changes via `nix build` to ensure static assets are correctly bundled in the Python package.
*   **Shotgun Pattern**: Perform exhaustive read-only research before executing file modifications.
*   **Grumpy Pragmatism**: Prioritize stability and correctness over clever abstractions.

## 5. Git Hygiene
*   Commit logically and granularly.
*   Maintain a clean workspace via `.gitignore`.
