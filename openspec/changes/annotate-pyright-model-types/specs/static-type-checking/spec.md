## ADDED Requirements

### Requirement: Model relation/FK warnings resolved by real annotations

`reportAttributeAccessIssue` warnings for Django reverse relations and `<fk>_id` attributes SHALL be resolved with bare class-level annotations on the model classes, typed from the actual ForeignKey definitions.

#### Scenario: reverse relation annotated correctly

- WHEN a model is the target of `ForeignKey(target, related_name="rel")`
- THEN the target model declares `rel: Manager[SourceModel]` and pyright no longer reports `reportAttributeAccessIssue` for `target_instance.rel`

#### Scenario: foreign-key id annotated

- WHEN a model declares `fk = ForeignKey(...)`
- THEN the model declares `fk_id: int` and pyright no longer reports the `<fk>_id` access

#### Scenario: annotations have no runtime effect

- WHEN the annotations are added
- THEN they are bare (no assignment), `Manager` is imported under `TYPE_CHECKING`, and `python manage.py makemigrations --check --dry-run` reports no new migrations

### Requirement: Un-annotatable warnings use rule-specific ignores

Warnings that cannot be expressed as a correct annotation SHALL use a rule-specific `# pyright: ignore[<rule>]` (not blanket `# type: ignore`).

#### Scenario: framework/stub residual ignored specifically

- WHEN a warning is from django-environ overloads, DRF ReturnDict/overrides, DRF test-client attributes, abstract-model Meta, the CheckConstraint stub mismatch, or celery `.delay`
- THEN that line carries a rule-specific `# pyright: ignore[<rule>]`

### Requirement: Zero-warning baseline with no behavior change

After this change the gate SHALL report 0 errors and 0 warnings, with no runtime behavior change.

#### Scenario: gate clean and app boots

- WHEN `pyright` and `python manage.py check` are run in the venv
- THEN pyright reports 0 errors and 0 warnings and the system check reports no issues

### Requirement: Mutually exclusive with the suppress change

This change and the sibling suppress change SHALL NOT both be merged.

#### Scenario: only one approach lands

- WHEN choosing between this annotate change and the suppress change
- THEN exactly one is merged
