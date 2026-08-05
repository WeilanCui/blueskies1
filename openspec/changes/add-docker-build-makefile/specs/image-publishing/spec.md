## ADDED Requirements

### Requirement: Production images are built from a single command

The repository SHALL provide a `Makefile` at its root that builds the production image
for every containerised service from one command, without the operator naming Dockerfiles,
build contexts, or build targets.

#### Scenario: Building all images

- **WHEN** the operator runs `make build`
- **THEN** the backend image is built from build context `./backend` at Dockerfile target `prod`
- **AND** the frontend image is built from build context `./frontend` at Dockerfile target `prod`
- **AND** each image is tagged with both the mutable tag and the revision tag

#### Scenario: Building a single service

- **WHEN** the operator runs `make build-backend`
- **THEN** only the backend image is built
- **AND** the frontend image is not built

### Requirement: Images carry a mutable tag and an immutable revision tag

Every built image SHALL carry two tags: a mutable tag defaulting to `latest`, and an
immutable tag derived from the current git revision. This allows a deployed image to be
traced back to the commit it was built from.

#### Scenario: Tagging from a clean checkout

- **WHEN** an image is built from a working tree with no uncommitted changes
- **THEN** the image is tagged `latest`
- **AND** the image is additionally tagged with the abbreviated commit hash of `HEAD`

#### Scenario: Tagging from a modified working tree

- **WHEN** an image is built from a working tree containing uncommitted changes
- **THEN** the revision tag is suffixed with `-dirty`
- **AND** the resulting tag therefore cannot be mistaken for a clean commit's image

#### Scenario: Building outside a git checkout

- **WHEN** the current revision cannot be determined from git
- **THEN** the build proceeds using a placeholder revision tag
- **AND** the build does not fail with an empty or malformed image tag

### Requirement: Images are published to a configurable registry

Built images SHALL be pushable to a container registry, defaulting to the local registry
at `direct:5000`, with both of the image's tags published.

#### Scenario: Publishing all images

- **WHEN** the operator runs `make push`
- **THEN** any image not already built is built first
- **AND** both the mutable tag and the revision tag of every image are pushed to the registry

#### Scenario: Image naming

- **WHEN** an image is built or pushed
- **THEN** its repository name is composed of the registry, the project prefix, and the service name
- **AND** the default names are `direct:5000/blueskies-backend` and `direct:5000/blueskies-frontend`

### Requirement: Build inputs are overridable without editing the Makefile

The registry, project prefix, mutable tag, container tool, build platform, and per-service
build target SHALL each be overridable as make variables on the command line.

#### Scenario: Publishing to an alternate registry under an explicit tag

- **WHEN** the operator runs `make push REGISTRY=registry.example.com TAG=v1.2.3`
- **THEN** the images are named and pushed under `registry.example.com`
- **AND** the mutable tag published is `v1.2.3` rather than `latest`

#### Scenario: Substituting the container tool

- **WHEN** the operator sets `DOCKER` to a `docker`-compatible executable
- **THEN** all build and push invocations use that executable

### Requirement: Local development remains unaffected

Introducing the Makefile SHALL NOT change how the local development stack is built or run.

#### Scenario: Compose workflow is unchanged

- **WHEN** the operator runs `docker compose up --build`
- **THEN** the services build their `dev` targets exactly as before the Makefile existed
- **AND** no Dockerfile or compose file was modified by this change

### Requirement: Locally built image tags can be removed

The Makefile SHALL provide a target that removes the image tags it created locally, and
that target SHALL be safe to run when those tags are already absent.

#### Scenario: Cleaning already-clean state

- **WHEN** the operator runs `make clean` twice in succession
- **THEN** the second invocation exits successfully
- **AND** it does not report an error for tags that no longer exist

### Requirement: Available targets and resolved names are discoverable

The Makefile SHALL be self-documenting: an operator can list its targets and inspect the
fully-qualified image names that the current variable values resolve to, without reading
the Makefile source.

#### Scenario: Listing targets

- **WHEN** the operator runs `make help`
- **THEN** the available targets are printed with a description of each

#### Scenario: Inspecting resolved image names

- **WHEN** the operator runs `make print-images`
- **THEN** the fully-qualified name and both tags of every image are printed
- **AND** no image is built as a side effect
