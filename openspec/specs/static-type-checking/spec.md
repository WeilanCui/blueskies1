# static-type-checking Specification

## Purpose

Define what the pyright static type-checking gate enforces for this codebase: genuinely-real type-safety warnings are fixed at their source with behavior-preserving changes, runtime behavior is left unchanged, and warnings that stem from stub-vs-pinned-library version mismatches are deliberately not "fixed" in code.

## Requirements

### Requirement: Real type-safety warnings are fixed at source

The genuinely-real pyright warnings (not stub/framework limitations) SHALL be resolved by behavior-preserving source fixes.

#### Scenario: seed_catalog return type narrowed

- WHEN pyright analyzes `core/management/commands/seed_catalog.py`
- THEN there is no `reportAttributeAccessIssue` for `.items()` on `int`, because `seed_catalog()` is typed `dict[str, dict[str, int]]`

#### Scenario: injected callable guarded

- WHEN pyright analyzes the two `self.ingest_compound_func(...)` call sites in `literature/discovery.py`
- THEN no `reportOptionalCall` is reported

#### Scenario: ElementTree text narrowed

- WHEN pyright analyzes `literature/ingestion/pubmed_client.py`
- THEN no `reportOptionalMemberAccess` is reported for `.text`

#### Scenario: test narrows optional before access

- WHEN pyright analyzes `literature/tests/test_literature_agent.py`
- THEN no `reportOptionalMemberAccess` is reported for `extraction`

### Requirement: Behavior is unchanged

The fixes SHALL NOT alter runtime behavior.

#### Scenario: system check and gate still pass

- WHEN `python manage.py check` and `pyright` are run with deps installed
- THEN the system check reports no issues and pyright reports 0 errors

### Requirement: Stub-version mismatches are not "fixed" in code

Warnings caused by a stub modeling a newer library API than the pinned dependency SHALL NOT be resolved by changing code in a way that breaks the pinned runtime.

#### Scenario: CheckConstraint left as-is

- WHEN the `CheckConstraint(check=...)` sites in `core/models/literature_discovery_target.py` are considered
- THEN the code keeps `check=` (correct for Django `<5.1`) and the warning is left for the sibling suppression change
