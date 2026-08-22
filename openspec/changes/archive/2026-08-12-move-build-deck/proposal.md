## Why

`build_deck.py` is a 24KB standalone pptx pitch-deck generator sitting at the repository root. It is not application code, has zero references anywhere in the repo, and pollutes the top-level alongside `docker-compose.yml` and the app directories. Relocating it to `tools/scripts/` keeps the root focused on the deployable system.

## What Changes

- Move `build_deck.py` → `tools/scripts/build_deck.py` (via `git mv`, preserving history).
- No code edits; the script has no in-repo importers or callers.

## Capabilities

### New Capabilities
<!-- None — repository housekeeping, no runtime behavior. -->

### Modified Capabilities
<!-- None. -->

## Impact

- Files: `build_deck.py` → `tools/scripts/build_deck.py`.
- No imports, Docker builds, CI, or settings reference the file (verified by grep), so nothing else changes.
- Anyone who ran `python build_deck.py` now runs `python tools/scripts/build_deck.py`.
