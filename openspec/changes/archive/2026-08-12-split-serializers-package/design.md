## Context

`core/serializers.py` re-exports ~25 serializer classes and 6 module-level helper functions, all imported elsewhere via `from core.serializers import …`. The only hard requirement is that this public import surface stays identical; physical layout is free to change. `core/models/` already demonstrates the target shape: a package whose `__init__.py` re-exports per-domain submodules.

## Goals / Non-Goals

**Goals:**
- One submodule per domain, mirroring `core/models/` module names.
- `core/serializers/__init__.py` re-exports the full public surface, flat and alphabetized.
- Provably identical exported name-set before and after.

**Non-Goals:**
- No change to any serializer field, validation, method body, or behavior.
- No change to which names are importable from `core.serializers`.
- No change to importers.

## Decisions

### Submodule mapping

Serializers and their co-located helpers move as follows (helpers travel with their domain, per the locked scope):

- `compound.py` — `CompoundAliasSerializer`, `CompoundIdentifierSerializer`, `CompoundStructureSerializer`, `ChemicalClassSerializer`, `ChemicalClassMembershipSerializer`, `PropertyAssertionSerializer`, `CompoundSerializer`
- `auth.py` — `AuthUserSerializer`, `SignupSerializer`, `LoginSerializer`, `auth_user_payload`, `_unique_username_from_email`, and the module-level `User = get_user_model()`
- `contact.py` — `ContactSubmissionSerializer`
- `location.py` — `LocationSerializer`, `WeatherSnapshotSerializer`, `ProfileLocationSerializer`
- `product.py` — `ProductSummarySerializer` (shared base used by formulation/routine/daily_checkin/reaction)
- `formulation.py` — `FormulationIngredientSerializer`, `FormulationSerializer`, `FormulationSubmitSerializer`
- `routine.py` — `RoutineItemSerializer`, `RoutineSerializer`, `RoutineAddProductSerializer`, `infer_routine_step_from_product`
- `daily_checkin.py` — `DailyProductUseSerializer`, `DailyCheckInSerializer`, `TodayCheckInSerializer`
- `reaction.py` — `ReactionEventSerializer`
- `catalog.py` — `CATALOG_SOURCE_PREFIX`, `catalog_slug`, `serialize_catalog_product`
- `intake.py` — `IntakeSerializer`, `intake_payload`

### Cross-module imports

`ProductSummarySerializer` lives in `product.py`; `formulation.py`, `routine.py`, `daily_checkin.py`, and `reaction.py` import it from `core.serializers.product`. `FormulationSerializer` is imported by `routine.py`, `daily_checkin.py`, `reaction.py`. `RoutineItemSerializer` is imported by `daily_checkin.py`. There are no import cycles: dependency order is `product → formulation → routine → daily_checkin`/`reaction`. Each submodule imports the model/service names it actually uses from `core.models` / `core.services.weather`, not the whole monolith's import block.

### Re-export

`__init__.py` imports every public name from its submodule and lists them in an alphabetized `__all__`, matching the style of `core/models/__init__.py`. `_unique_username_from_email` is module-private (leading underscore) and not re-exported.

## Risks / Trade-offs

- **Accidental name drop / changed behavior** during the move → ImportError or broken endpoint. Mitigated by: (a) the existing test suite, (b) `manage.py check`, (c) verifying the importable name-set from `core.serializers` is unchanged.
- **Import cycle** if a submodule imports a downstream one. Mitigated by the acyclic dependency order above (`product` is a leaf; nothing imports upward).
- **Merge churn** with other open serializer-touching PRs. Accepted; resolved by rebase if needed.
