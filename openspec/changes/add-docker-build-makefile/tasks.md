## 1. Makefile scaffolding

- [ ] 1.1 Create `Makefile` at the repository root with `.DEFAULT_GOAL := help` and a `.PHONY` line covering every target
- [ ] 1.2 Declare the overridable variables with `?=`: `REGISTRY` (`direct:5000`), `PROJECT` (`blueskies`), `TAG` (`latest`), `DOCKER` (`docker`), `PLATFORM` (empty), `BUILD_ARGS` (empty), `BACKEND_TARGET` (`prod`), `FRONTEND_TARGET` (`prod`)
- [ ] 1.3 Compute `REV` with `:=`: abbreviated `HEAD` hash, suffixed `-dirty` when `git status --porcelain` is non-empty, falling back to `nogit` when `git rev-parse` fails
- [ ] 1.4 Derive `BACKEND_IMAGE` and `FRONTEND_IMAGE` as `$(REGISTRY)/$(PROJECT)-backend` and `$(REGISTRY)/$(PROJECT)-frontend`, and derive the `--platform` flag so it expands to nothing when `PLATFORM` is empty

## 2. Build targets

- [ ] 2.1 Add `build-backend`: one `$(DOCKER) build` over context `./backend` with `--target $(BACKEND_TARGET)`, both `-t $(BACKEND_IMAGE):$(TAG)` and `-t $(BACKEND_IMAGE):$(REV)`, plus the platform and `BUILD_ARGS` passthroughs
- [ ] 2.2 Add `build-frontend`: the same shape over context `./frontend` with `--target $(FRONTEND_TARGET)`
- [ ] 2.3 Add `build` depending on both

## 3. Publish and cleanup targets

- [ ] 3.1 Add `push-backend` depending on `build-backend`, pushing both `$(TAG)` and `$(REV)` tags
- [ ] 3.2 Add `push-frontend` depending on `build-frontend`, pushing both tags
- [ ] 3.3 Add `push` depending on both
- [ ] 3.4 Add `clean` removing all four local tags, suppressing failure so a second run exits 0

## 4. Discoverability

- [ ] 4.1 Add `print-images` echoing both fully-qualified image names with both tags, building nothing
- [ ] 4.2 Add `help` listing every target with a one-line description, driven by `##` comments on the target lines so it cannot drift from the actual targets

## 5. Documentation

- [ ] 5.1 Add a "Building and publishing images" section to `README.md` near the existing Docker instructions, covering `make build` / `make push` and the common variable overrides
- [ ] 5.2 Document the two registry prerequisites in that section: `direct` must resolve on the build host, and the Docker daemon needs `direct:5000` under `insecure-registries` in `/etc/docker/daemon.json` followed by a daemon restart

## 6. Verification

- [ ] 6.1 Run `make help` and `make print-images`; confirm the target list renders and the names resolve to `direct:5000/blueskies-backend` and `direct:5000/blueskies-frontend` with the current short SHA
- [ ] 6.2 Run `make build`; confirm `docker images | grep blueskies` shows four rows (two images x `latest` + revision)
- [ ] 6.3 Confirm the built backend image runs gunicorn via `deploy/entrypoint.sh`, and that the frontend image contains `server.js` and exposes 5000
- [ ] 6.4 Verify override plumbing: `make print-images REGISTRY=localhost:5000 TAG=test` reports the overridden names
- [ ] 6.5 Verify the dirty-tree rule: with an uncommitted edit present, `make print-images` reports a `-dirty` revision tag
- [ ] 6.6 Check registry reachability with `curl -s http://direct:5000/v2/_catalog` before pushing; if it fails, resolve the prerequisites from 5.2 first
- [ ] 6.7 Run `make push`, then confirm via `curl -s http://direct:5000/v2/_catalog` and `curl -s http://direct:5000/v2/blueskies-backend/tags/list` that both repositories and both tags are present
- [ ] 6.8 Run `make clean` twice; confirm the second invocation exits 0
- [ ] 6.9 Confirm no regression to local development: `docker compose up --build` still builds the `dev` targets and the stack comes up
