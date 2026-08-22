## ADDED Requirements

### Requirement: Score a single formulation for the authenticated user

The system SHALL provide `POST /api/recommendations/score/` that scores one formulation against the authenticated user's active profile constraints and returns the match detail. The endpoint SHALL require authentication and SHALL resolve (or create) the caller's profile automatically.

#### Scenario: Authenticated user scores a formulation

- **WHEN** an authenticated user POSTs `{ "formulation_id": <existing id> }`
- **THEN** the system responds `200` with `final_score`, `excluded`, `reasons`, and the `warnings`, `penalties`, and `boosts` impact groups for that formulation

#### Scenario: Formulation matches a hard exclusion

- **WHEN** the scored formulation matches an `EXCLUDE` constraint on the user's profile
- **THEN** the response has `excluded: true`, `final_score: 0`, and a reason explaining the exclusion

#### Scenario: User has no constraints yet

- **WHEN** an authenticated user with no active constraints scores a formulation
- **THEN** the system responds `200` with the base score and empty impact groups

#### Scenario: Unknown formulation id

- **WHEN** the request references a formulation id that does not exist
- **THEN** the system responds `404`

#### Scenario: Invalid or missing formulation id

- **WHEN** the request body omits `formulation_id` or supplies a non-integer value
- **THEN** the system responds `400` with a validation error

#### Scenario: Unauthenticated request

- **WHEN** an unauthenticated client calls the endpoint
- **THEN** the system responds `403`

### Requirement: Rank the catalog for the authenticated user

The system SHALL provide `GET /api/recommendations/` that scores every formulation with a resolved product against the authenticated user's profile, returns them best-first, and paginates the result. Hard-excluded formulations SHALL be omitted by default.

#### Scenario: Authenticated user ranks the catalog

- **WHEN** an authenticated user requests the endpoint
- **THEN** the system responds `200` with a paginated list of matches sorted by descending `final_score`, each carrying formulation id, product name and brand, `final_score`, `excluded`, and top reasons

#### Scenario: Excluded products hidden by default

- **WHEN** the user requests the endpoint without `include_excluded`
- **THEN** formulations that match a hard `EXCLUDE` constraint are absent from the results

#### Scenario: Include excluded products on request

- **WHEN** the user requests the endpoint with `?include_excluded=true`
- **THEN** hard-excluded formulations are included and sorted after non-excluded ones

#### Scenario: Results are paginated

- **WHEN** the catalog has more than one page of formulations
- **THEN** the system returns at most the page size (20) per page with pagination metadata

#### Scenario: Empty catalog

- **WHEN** no formulations with a resolved product exist
- **THEN** the system responds `200` with an empty paginated result

#### Scenario: Unauthenticated request

- **WHEN** an unauthenticated client calls the endpoint
- **THEN** the system responds `403`

### Requirement: Frontend surfaces the recommendations

The frontend SHALL let an authenticated user view their ranked recommendations and see a per-product match score, consuming the endpoints via TanStack Query and following mobile-first, explicit-state conventions.

#### Scenario: For You ranked page

- **WHEN** an authenticated user opens the "For You" recommendations page
- **THEN** the page fetches the ranked catalog and renders loading, empty, error, and populated states, with each item showing its product and match score, at phone width without horizontal overflow

#### Scenario: Score badge on product detail

- **WHEN** an authenticated user views a product or a scan result
- **THEN** a score badge displays that formulation's match score for the user, visually distinguishing excluded and cautioned products
