## 1. Makefile scaffolding

- [x] 1.1 Create `Makefile` at the repository root with `.DEFAULT_GOAL := help` and a `.PHONY` line covering every target
- [x] 1.2 Declare the overridable variables with `?=`: `REGISTRY` (`direct:5000`), `PROJECT` (`blueskies`), `TAG` (`latest`), `DOCKER` (`docker`), `PLATFORM` (empty), `BUILD_ARGS` (empty), `BACKEND_TARGET` (`prod`), `FRONTEND_TARGET` (`prod`)
- [x] 1.3 Compute `REV` with `:=`: abbreviated `HEAD` hash, suffixed `-dirty` when `git status --porcelain` is non-empty, falling back to `nogit` when `git rev-parse` fails
- [x] 1.4 Derive `BACKEND_IMAGE` and `FRONTEND_IMAGE` as `$(REGISTRY)/$(PROJECT)-backend` and `$(REGISTRY)/$(PROJECT)-frontend`, and derive the `--platform` flag so it expands to nothing when `PLATFORM` is empty

## 2. Build targets

- [x] 2.1 Add `build-backend`: one `$(DOCKER) build` over context `./backend` tagging both `-t $(BACKEND_IMAGE):$(TAG)` and `-t $(BACKEND_IMAGE):$(REV)`, plus the platform, target and `BUILD_ARGS` passthroughs
- [x] 2.2 Add `build-frontend`: the same shape over context `./frontend`
- [x] 2.3 Add `build` depending on both

## 3. Publish and cleanup targets

- [x] 3.1 Add `push-backend` depending on `build-backend`, pushing both `$(TAG)` and `$(REV)` tags
- [x] 3.2 Add `push-frontend` depending on `build-frontend`, pushing both tags
- [x] 3.3 Add `push` depending on both
- [x] 3.4 Add `clean` removing all four local tags, suppressing failure so a second run exits 0

## 4. Discoverability

- [x] 4.1 Add `print-images` echoing both fully-qualified image names with both tags, building nothing
- [x] 4.2 Add `help` listing every target with a one-line description, driven by `##` comments on the target lines so it cannot drift from the actual targets

## 5. Deploy targets

- [x] 5.1 Add `deploy` (`docker stack deploy -c $(STACK_FILE)`), `deploy-status`, and a `release` recipe that invokes `push` then `deploy TAG=$(REV)` as sub-makes, so ordering holds under `make -j` and the deployed image names the commit

## 6. Documentation

- [x] 6.1 Add a "Building and publishing images" section to `README.md` near the existing Docker instructions, covering `make build` / `make push` and the common variable overrides
- [x] 6.2 Document the two registry prerequisites in that section: `direct` must resolve on the build host, and the Docker daemon needs `direct:5000` under `insecure-registries` in `/etc/docker/daemon.json` followed by a daemon restart

## 7. Verification

- [x] 7.1 Run `make help` and `make print-images`; confirm the target list renders and the names resolve to `direct:5000/blueskies-backend` and `direct:5000/blueskies-frontend` with the current short SHA
- [x] 7.2 Run `make build`; confirm `docker images | grep blueskies` shows four rows (two images x `latest` + revision)
- [x] 7.3 Confirm both built images contain the expected application code and expose their documented ports
- [x] 7.4 Verify override plumbing: `make print-images REGISTRY=localhost:5000 TAG=test` reports the overridden names
- [x] 7.5 Verify the dirty-tree rule: with an uncommitted edit present, `make print-images` reports a `-dirty` revision tag
- [x] 7.6 Check registry reachability with `curl -s http://direct:5000/v2/_catalog` before pushing; if it fails, resolve the prerequisites from 6.2 first
- [x] 7.7 Run `make push`, then confirm via `curl -s http://direct:5000/v2/_catalog` and `curl -s http://direct:5000/v2/blueskies-backend/tags/list` that both repositories and both tags are present
- [x] 7.8 Run `make clean` twice; confirm the second invocation exits 0
- [x] 7.9 Confirm no regression to local development: `docker compose up --build` still builds the `dev` targets and the stack comes up
