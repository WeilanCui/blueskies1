## ADDED Requirements

### Requirement: Standalone tooling lives under tools/scripts

Non-application, standalone scripts SHALL NOT reside at the repository root. The pitch-deck generator SHALL live at `tools/scripts/build_deck.py`.

#### Scenario: build_deck relocated

- **WHEN** inspecting the repository tree
- **THEN** `build_deck.py` does not exist at the repo root
- **AND** `tools/scripts/build_deck.py` exists with identical content

#### Scenario: No references break

- **WHEN** grepping the repo for `build_deck`
- **THEN** no source file, Docker build, CI config, or doc references the old root path
