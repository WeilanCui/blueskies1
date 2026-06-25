## ADDED Requirements

### Requirement: Zero-warning baseline via targeted suppression

Every remaining framework/stub-limitation warning SHALL be suppressed at its source with a rule-specific `# pyright: ignore[<rule>]` comment, bringing the gate to zero warnings.

#### Scenario: gate reports no warnings

- WHEN `pyright` is run in the project venv after this change
- THEN it reports 0 errors and 0 warnings

#### Scenario: suppressions are rule-specific

- WHEN a suppression comment is inspected
- THEN it names the specific rule(s) being ignored (e.g. `# pyright: ignore[reportAttributeAccessIssue]`), not a blanket `# type: ignore`

#### Scenario: unrelated errors still surface

- WHEN a new, different type error is introduced on a line that carries a rule-specific ignore
- THEN pyright still reports that new error

### Requirement: No behavior change

The suppression SHALL be comment-only with no runtime effect.

#### Scenario: system check passes

- WHEN `python manage.py check` runs with deps installed
- THEN it reports no issues

### Requirement: Mutually exclusive with the annotate change

This change and the sibling annotate change SHALL NOT both be merged.

#### Scenario: only one approach lands

- WHEN choosing between this suppression change and the annotate change
- THEN exactly one is merged to resolve the remaining warnings
