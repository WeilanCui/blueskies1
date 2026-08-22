## 1. Move the file

- [x] 1.1 `mkdir -p tools/scripts` and `git mv build_deck.py tools/scripts/build_deck.py`.

## 2. Verify

- [x] 2.1 Confirm `build_deck.py` no longer at repo root; `tools/scripts/build_deck.py` exists.
- [x] 2.2 `grep -rn build_deck` finds no reference to the old root path (outside this OpenSpec change).
- [x] 2.3 `python -m py_compile tools/scripts/build_deck.py` succeeds (file still parses).
