## ADDED Requirements

### Requirement: Model exports are alphabetically ordered

`core/models/__init__.py` SHALL list its import blocks (by module), the names within each block, and `__all__` in alphabetical order, while preserving the exact set of exported names.

#### Scenario: Ordering is alphabetical

- **WHEN** reading `core/models/__init__.py`
- **THEN** the `from core.models.<module>` blocks appear in alphabetical module order
- **AND** the names imported within each block are in alphabetical order
- **AND** `__all__` is in alphabetical order

#### Scenario: Export set unchanged

- **WHEN** comparing the set of names in `__all__` before and after the change
- **THEN** the two sets are identical (no name added or removed)
- **AND** `manage.py check` reports no issues and `makemigrations --check` detects no changes
