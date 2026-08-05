## Context

`backend/Dockerfile` and `frontend/Dockerfile` were recently split into named stages
(`base -> dev | prod` and `deps -> dev | builder -> prod` respectively). `docker-compose.yml`
pins `target: dev` on every built service, so the local development flow is fully served.
Nothing in the repository builds or publishes the `prod` stages — there is no Makefile, no
CI workflow, and no reference to any registry anywhere in the tree.

The deployment target is a Docker Swarm platform fed from a local registry at `direct:5000`.
Constraints that shape this design:

- The two build contexts differ (`./backend`, `./frontend`) and their `prod` stages are not
  interchangeable — the frontend prod stage is a fresh `node:22-bookworm-slim` populated
  from a `builder` stage, and listens on port 5000, while the backend prod stage extends
  `base` and listens on 8000.
- `frontend/Dockerfile` may gain build arguments shortly (Next bakes `rewrites()`
  destinations into the route manifest at build time, so `SERVER_API_BASE_URL` must be
  present during `next build`). The Makefile must accommodate that without being rewritten.
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

### Build the `prod` stage, not the default stage

Both Dockerfiles now define multiple stages, and the last stage in each file is `prod`.
Relying on that positional default is fragile — appending a stage would silently change
what gets published. Every build therefore passes `--target` explicitly, held in per-image
variables (`BACKEND_TARGET`, `FRONTEND_TARGET`, both defaulting to `prod`) so a caller can
publish a `dev` image for debugging without editing the file.

*Alternative considered:* omit `--target` and let the last stage win. Rejected: implicit,
and breaks the moment a stage is appended.

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

Rather than enumerating build arguments the Dockerfiles do not yet declare, a single
`BUILD_ARGS` variable is interpolated into every `docker build`. When the frontend gains
`ARG SERVER_API_BASE_URL`, publishing becomes
`make push BUILD_ARGS='--build-arg SERVER_API_BASE_URL=http://backend:8000'` with no
change to the Makefile. `PLATFORM` is handled the same way: empty by default, expanding to
`--platform <value>` only when set.

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
- **Frontend prod build runs `npm run build`, which is slow and needs network on a cold
  cache** → Inherent to the Dockerfile, not to this change. The `deps` stage caches
  `node_modules` across builds.
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
