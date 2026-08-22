## Context

`build_deck.py` lives at repo root but is a one-off pitch-deck generator (`python-pptx`), unrelated to the Django/Next.js app. `grep -rn build_deck` across `*.py`, compose, Dockerfiles, and docs returns zero hits — nothing imports or invokes it.

## Goals / Non-Goals

**Goals:**
- Remove the stray file from repo root; place it under `tools/scripts/`.
- Preserve git history for the file.

**Non-Goals:**
- No edits to the script's contents.
- No new dependency management for `python-pptx` (it was never wired into the app).
- Not deleting the script (the user wants it kept, just relocated).

## Decisions

- Use `git mv build_deck.py tools/scripts/build_deck.py` so history follows the file. Create `tools/scripts/` (new directory).
- The destination is `tools/scripts/` per the request; no `__init__.py` is added — it is a runnable script, not an importable package.

## Risks / Trade-offs

- **Stale muscle memory**: anyone invoking `python build_deck.py` must use the new path. Negligible — it's a manual, occasional tool with no automation depending on it.
