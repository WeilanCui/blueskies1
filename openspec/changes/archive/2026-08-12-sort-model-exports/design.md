## Context

`core/models/__init__.py` re-exports 66 names across 15 module imports, in an order that grew organically. The only requirement is that the re-export surface stays identical; ordering is free to change.

## Goals / Non-Goals

**Goals:**
- Deterministic alphabetical ordering of import blocks, names-per-block, and `__all__`.
- Provably identical exported name-set before and after.

**Non-Goals:**
- No changes to any model module, field, or behavior.
- No change to which names are exported.

## Decisions

- Ordering rules: import blocks sorted by module path; names within each block sorted; `__all__` sorted — all case-sensitive ASCII sort (Python default `sorted`).
- Generated mechanically and guarded: the change was produced by parsing the existing file, asserting `union(imported names) == set(__all__)`, re-emitting sorted, then re-parsing to assert the set is unchanged. This rules out an accidental dropped/added name.

## Risks / Trade-offs

- **Accidental name drop** during reorder → ImportError elsewhere. Mitigated by the set-equality guard and by `manage.py check` (loads every model through this file).
- **Merge conflict** with #18/#19 which rewrite the same file. Accepted; resolved by rebase after those merge.
