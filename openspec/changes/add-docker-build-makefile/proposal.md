## Why

The repository has Dockerfiles for both services but no way to produce and publish their
images. Every documented workflow is `docker compose up --build`, which builds under
compose-generated names and never pushes anywhere. Deploying means retyping long
`docker build`/`docker tag`/`docker push` invocations by hand, with no guarantee that the
tag on the registry corresponds to a known commit.

## What Changes

- Add a top-level `Makefile` that builds both service images and pushes the results to
  the local registry at `direct:5000`.
- Each image is tagged twice per build: a mutable `latest` (overridable via `TAG=`) and an
  immutable short git SHA, so a deployed image can always be traced back to a commit.
- All inputs are overridable make variables (`REGISTRY`, `PROJECT`, `TAG`, `DOCKER`,
  `PLATFORM`, per-image `TARGET`), so the same Makefile serves a different registry or a
  one-off tag without edits.
- A dirty working tree appends `-dirty` to the SHA tag, so an image built from
  uncommitted changes can never masquerade as a clean commit.
- Document the registry prerequisites in `README.md`: `direct:5000` is plain HTTP and
  requires a Docker daemon `insecure-registries` entry plus name resolution for `direct`.
- Add `deploy`, `release` and `deploy-status` targets wrapping `docker stack deploy` against
  `service-compose.yml`. `release` runs `push` and then deploys the revision tag it just
  published, so the running stack names the commit it came from; `deploy` alone redeploys
  the stack file without rebuilding.
- The stack file's image references interpolate `REGISTRY`, `PROJECT` and `TAG`, which the
  Makefile exports, so an override cannot push one set of images and deploy another.
- No changes to `backend/Dockerfile`, `frontend/Dockerfile`, or `docker-compose.yml`. The
  local development flow is untouched.

## Capabilities

### New Capabilities
- `image-publishing`: Building the production container images for each service and
  publishing them to a container registry under deterministic, traceable tags.

### Modified Capabilities

None. No existing spec's requirements change; `static-type-checking` is unaffected.

## Impact

- **New file**: `Makefile` at the repository root. It is the only implementation artifact.
- **Modified**: `README.md` gains a "Building and publishing images" section.
- **Reads but does not modify**: `backend/Dockerfile` and `frontend/Dockerfile`, and the
  build contexts `./backend` and `./frontend` that `docker-compose.yml` already establishes.
- **External dependency**: a reachable registry at `direct:5000`. The Makefile does not
  configure the Docker daemon; `insecure-registries` is a root-owned host change outside
  the scope of a build script.
- **Tooling**: requires `docker` (or a drop-in set via `DOCKER=`) and `git` on PATH. Adds
  no Python or Node dependencies, and does not touch CI (the repo has no workflows).
