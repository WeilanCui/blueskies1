## Context

`backend/Dockerfile` and `frontend/Dockerfile` are single-stage and dev-oriented.
`docker-compose.yml` builds them directly, so the local development flow is fully served.
Nothing in the repository builds or publishes images for deployment — there is no
Makefile, no CI workflow, and no reference to any registry anywhere in the tree.

The deployment target is a Docker Swarm platform fed from a local registry at `direct:5000`.
Constraints that shape this design:

- The two build contexts differ (`./backend`, `./frontend`) and are not interchangeable.
- The Dockerfiles are expected to gain named stages (a production stage per service) and
  build arguments later. The Makefile must accommodate both without being rewritten.
- `direct:5000` is a plain-HTTP registry. Docker refuses to push to it unless the daemon
  is configured, which is a root-owned host change.

## Goals / Non-Goals

**Goals:**

- One command to build both production images; one command to publish them.
- Every published image traceable to a commit, and impossible to confuse with an image
  built from uncommitted work.
- Every input overridable from the command line, so the same file serves a different
  registry, tag, container tool, or platform without edits.
- Zero impact on the compose development flow.

**Non-Goals:**

- Wrapping development commands (`up`, `down`, `migrate`, `test`, `lint`). The Makefile is
  build-and-publish only; `CLAUDE.md` and `README.md` already document the compose commands.
- Modifying any Dockerfile or `docker-compose.yml`.
- Configuring the Docker daemon's `insecure-registries`, creating the registry, or
  deploying the pushed images. Those are host- and platform-level concerns.
- Multi-architecture manifests via buildx. A `PLATFORM` passthrough is provided for the
  single-arch case; true multi-arch is a later change if the platform demands it.
- CI integration. The repository has no workflows; adding one is a separate change.

## Decisions

### Stage selection is explicit when it happens at all

The Dockerfiles are single-stage today, so no `--target` is passed and the flag expands to
nothing. Per-image variables (`BACKEND_TARGET`, `FRONTEND_TARGET`) exist and are empty by
default. When the Dockerfiles gain named stages, the operator sets the variable rather than
the Makefile relying on the last stage winning — that positional default is fragile, since
appending a stage would silently change what gets published.

*Alternative considered:* hard-code a `prod` target now, in anticipation. Rejected: it
breaks every build until those stages actually exist.

### Two tags per build, applied in a single `docker build`

`docker build` accepts repeated `-t` flags, so both tags are produced by one invocation
rather than a build followed by a `docker tag`. This guarantees the two tags always denote
the identical image, and halves the number of commands.

*Alternative considered:* build with the SHA tag, then `docker tag` to `latest`. Equivalent
in effect but more moving parts, and a partial failure can leave the two tags divergent.

### Revision tag derived from git, with `-dirty` and a fallback

`REV` is computed with `:=` (immediate assignment) so `git rev-parse` runs once per make
invocation rather than once per use. Three cases:

- clean checkout → abbreviated `HEAD` hash
- `git status --porcelain` non-empty → hash with `-dirty` appended
- `git rev-parse` fails (no git, no commits) → literal `nogit`

The fallback matters because an empty tag makes `docker build -t name:` fail with an
opaque parse error. `-dirty` matters because publishing uncommitted work under a clean
commit's tag makes the registry lie about what is deployed.

*Alternative considered:* refuse to build when the tree is dirty. Rejected as too strict —
iterating on a deployment inevitably means pushing uncommitted builds; they just need to be
labelled as such.

### `push` depends on `build`

`push-backend` declares `build-backend` as a prerequisite, so `make push` on a clean
checkout does the right thing. Since `.PHONY` targets always re-run, this means `make push`
always rebuilds; that is the safe default (docker's layer cache makes a no-op rebuild
cheap) and avoids publishing a stale local image.

### Generic `BUILD_ARGS` passthrough

Rather than enumerating build arguments the Dockerfiles do not declare, a single
`BUILD_ARGS` variable is interpolated into every `docker build`. If the frontend later
gains an `ARG`, publishing becomes
`make push BUILD_ARGS='--build-arg SERVER_API_BASE_URL=http://backend:8000'` with no
change to the Makefile. `PLATFORM` and the two target variables are handled the same way:
empty by default, expanding to their flag only when set.

### Image naming: `$(REGISTRY)/$(PROJECT)-$(service)`

Yields `direct:5000/blueskies-backend` and `direct:5000/blueskies-frontend`. A flat
prefix rather than a nested path (`direct:5000/blueskies/backend`) because plain
`registry:2` handles both, but flat names avoid ambiguity with registries that treat the
first path segment as an organisation.

### Registry prerequisites documented, not automated

`README.md` gains a section stating that `direct` must resolve and that the daemon needs
`direct:5000` in `insecure-registries`. The Makefile does not attempt either. Editing
`/etc/docker/daemon.json` and restarting the daemon requires root and affects every
container on the host — far outside what running `make` should be permitted to do.

## Risks / Trade-offs

- **Push fails with `http: server gave HTTP response to HTTPS client`** → Documented in
  README with the exact `daemon.json` fix. `make push` failing loudly here is correct; a
  Makefile that silently reconfigured the daemon would be worse.
- **`direct` does not resolve on the build host** → Documented; `REGISTRY` is overridable,
  so an IP or alternate hostname works without editing the file.
- **`make push` always rebuilds** → Accepted. Docker's cache makes the no-op case fast, and
  the alternative (publishing a stale local image) is a worse failure mode.
- **Frontend builds install dependencies and need network on a cold cache** → Inherent to
  the Dockerfile, not to this change. Docker's layer cache covers the warm case.
- **`latest` is mutable, so two commits can both claim it** → This is why the revision tag
  exists and is always published alongside. Deployments should reference the revision tag.
- **Building from a dirty tree produces a `-dirty` tag that cannot be reproduced from git**
  → Deliberate: the tag is honest about it rather than silently reproducible-looking.

## Migration Plan

Additive; nothing to migrate. The Makefile is new and no existing file changes behaviour.
Rollback is deleting `Makefile` and reverting the `README.md` section — no build artefacts,
state, or schema are involved. Images already pushed to the registry are unaffected either way.

## Open Questions

- **Default goal**: this design sets `.DEFAULT_GOAL := help`, so a bare `make` prints usage
  rather than building or publishing. Publishing to a shared registry should be an explicit
  act, never the result of typing `make` by reflex.
- Whether the celery and celery-beat services warrant their own image tags. They currently
  share `./backend` as build context and differ only in `command:`, so one backend image
  serves all three. Revisit only if their dependencies diverge.
