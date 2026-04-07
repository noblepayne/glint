# glint V0.2 Plan

## Completed
- [x] Fix server JS async/await for selectFilter (prevents UI lock-up)
- [x] Create glint/vision.py with Gemma 4 integration
- [x] Add vision endpoints to server.py (/vision/auto-fix, /vision/refine)
- [x] Add Vision UI section to web server
- [x] Implement glint auto-fix CLI command
- [x] Server: Add error handling for /upload and /apply endpoints

## Next (V0.2+)
- [ ] Test vision integration end-to-end (requires running server with LLM access)
- [ ] Persist "Save as New Filter" to filters.py or local config
- [ ] Add export to .cube functionality in UI

## Architecture Notes
- LLM endpoint: http://prism:8080/openai/v1 (no auth)
- Model: openrouter/google/gemma-4-31b-it
- Vision integration: iterative refinement (1-5 rounds)