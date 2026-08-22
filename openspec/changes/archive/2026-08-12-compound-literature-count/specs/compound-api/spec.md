## ADDED Requirements

### Requirement: literature_count is computed at the database

`CompoundSerializer` SHALL report `literature_count` using a database-level count (a queryset annotation) rather than loading all `literature_links` rows, and the compound list endpoint SHALL NOT issue a per-compound count query.

#### Scenario: Correct count value

- **WHEN** a compound with N linked literature references is serialized
- **THEN** `literature_count` equals N

#### Scenario: No per-compound count queries in the list view

- **WHEN** the compound list endpoint serializes a page containing multiple compounds
- **THEN** the number of database queries does not grow per compound on account of `literature_count` (the count comes from the annotation on the list query, not one query per compound)

#### Scenario: Correct without annotation

- **WHEN** `CompoundSerializer` is used on a `Compound` instance that was not annotated with `literature_count`
- **THEN** `literature_count` is still correct (computed via a single count query)
- **AND** all link rows are not loaded into memory to produce it
