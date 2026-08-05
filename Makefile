# Builds the container images and publishes them to a registry.
#
# Local development does not use this file — `docker compose up --build` builds
# its own images and is unaffected by anything here.
#
# Every variable is overridable on the command line:
#   make push
#   make push TAG=v1.2.3
#   make build REGISTRY=localhost:5000 PLATFORM=linux/amd64
#   make push BUILD_ARGS='--build-arg SERVER_API_BASE_URL=http://backend:8000'
#   make release STACK=blueskies1

REGISTRY        ?= direct:5000
PROJECT         ?= blueskies
TAG             ?= latest
DOCKER          ?= docker
PLATFORM        ?=
BUILD_ARGS      ?=
# Both Dockerfiles are multi-stage. The stage is named explicitly rather than left to
# the last-stage-wins default, so appending a stage cannot silently change what ships.
# Set to dev to publish a development image for debugging.
BACKEND_TARGET  ?= prod
FRONTEND_TARGET ?= prod

# Swarm deployment. STACK is the stack name; the service DNS names inside the stack
# are unaffected by it.
STACK           ?= blueskies1
STACK_FILE      ?= service-compose.yml
# --with-registry-auth forwards this client's registry credentials to the swarm
# managers, which is what lets the other nodes pull from a private registry.
DEPLOY_FLAGS    ?= --detach=true --with-registry-auth

# Resolved once per invocation rather than once per use.
REV := $(shell git rev-parse --short HEAD 2>/dev/null)
ifeq ($(strip $(REV)),)
# No git, or no commits yet. An empty tag would make `docker build -t name:` fail
# with an opaque parse error, so name the condition instead.
REV := nogit
else
ifneq ($(strip $(shell git status --porcelain 2>/dev/null)),)
# An image built from uncommitted work must never claim a clean commit's tag.
REV := $(REV)-dirty
endif
endif

BACKEND_IMAGE  := $(REGISTRY)/$(PROJECT)-backend
FRONTEND_IMAGE := $(REGISTRY)/$(PROJECT)-frontend

# The stack file names its images as ${REGISTRY:-...}/${PROJECT:-...}-x:${TAG:-latest},
# which `docker stack deploy` interpolates from this process's environment. Exporting
# them is what keeps a `make deploy REGISTRY=...` from pushing one set of images and
# deploying another.
export REGISTRY
export PROJECT
export TAG

# These expand to nothing unless their variable is set.
PLATFORM_FLAG        := $(if $(strip $(PLATFORM)),--platform $(strip $(PLATFORM)),)
BACKEND_TARGET_FLAG  := $(if $(strip $(BACKEND_TARGET)),--target $(strip $(BACKEND_TARGET)),)
FRONTEND_TARGET_FLAG := $(if $(strip $(FRONTEND_TARGET)),--target $(strip $(FRONTEND_TARGET)),)

.DEFAULT_GOAL := help
.PHONY: help build build-backend build-frontend push push-backend push-frontend \
        deploy release deploy-status clean print-images

## --- build ------------------------------------------------------------------

# Both tags come from one build, which guarantees they denote the same image.

build-backend: ## Build the backend image (serves backend, celery and celery-beat)
	$(DOCKER) build $(PLATFORM_FLAG) $(BACKEND_TARGET_FLAG) $(BUILD_ARGS) \
		-t $(BACKEND_IMAGE):$(TAG) \
		-t $(BACKEND_IMAGE):$(REV) \
		./backend

build-frontend: ## Build the frontend image (Next.js app)
	$(DOCKER) build $(PLATFORM_FLAG) $(FRONTEND_TARGET_FLAG) $(BUILD_ARGS) \
		-t $(FRONTEND_IMAGE):$(TAG) \
		-t $(FRONTEND_IMAGE):$(REV) \
		./frontend

build: build-backend build-frontend ## Build both images

## --- publish ----------------------------------------------------------------

# Each push target rebuilds first, so `make push` works from a clean checkout and
# never publishes a stale local image. Docker's layer cache makes the no-op case
# cheap.

push-backend: build-backend ## Build and push the backend image (both tags)
	$(DOCKER) push $(BACKEND_IMAGE):$(TAG)
	$(DOCKER) push $(BACKEND_IMAGE):$(REV)

push-frontend: build-frontend ## Build and push the frontend image (both tags)
	$(DOCKER) push $(FRONTEND_IMAGE):$(TAG)
	$(DOCKER) push $(FRONTEND_IMAGE):$(REV)

push: push-backend push-frontend ## Build and push both images

## --- deploy -----------------------------------------------------------------

# `deploy` deliberately does NOT depend on `push`: redeploying after editing only the
# stack file should not rebuild images, and the swarm pulls from the registry rather
# than from this machine. Use `release` (or `make push deploy`) to do both.
#
# The stack must be deployed from a swarm manager. Deploying a new hostname also needs
# `docker service update --force traefik_traefik` afterwards -- Traefik's replicas race
# on ACME and only the winner holds the new certificate. That is left manual because it
# restarts the ingress for every stack on the swarm, not just this one.

deploy: ## Deploy the stack to Docker Swarm (does not build or push)
	$(DOCKER) stack deploy -c $(STACK_FILE) $(DEPLOY_FLAGS) $(STACK)

# Two sub-makes rather than `release: push deploy`: prerequisites of one target may run
# concurrently under `make -j`, which would deploy while the images were still building
# and quietly start the previous release. A recipe is ordered by definition.
#
# TAG=$(REV) is what makes the running stack traceable: the deployed image is the commit
# it was built from, and an image built from uncommitted work deploys as <sha>-dirty
# rather than hiding behind `latest`.
release: ## Build, push, then deploy the revision that was just built
	$(MAKE) push
	$(MAKE) deploy TAG=$(REV)

deploy-status: ## Show the deployed services and any task errors
	@$(DOCKER) stack services $(STACK)
	@echo ""
	@$(DOCKER) stack ps $(STACK) --no-trunc \
		--format 'table {{.Name}}\t{{.Node}}\t{{.CurrentState}}\t{{.Error}}' | head -20

## --- housekeeping -----------------------------------------------------------

clean: ## Remove the locally built image tags (safe to re-run)
	-@$(DOCKER) rmi $(BACKEND_IMAGE):$(TAG) $(BACKEND_IMAGE):$(REV) \
		$(FRONTEND_IMAGE):$(TAG) $(FRONTEND_IMAGE):$(REV) 2>/dev/null || true

print-images: ## Print the image names the current variables resolve to
	@echo "$(BACKEND_IMAGE):$(TAG)"
	@echo "$(BACKEND_IMAGE):$(REV)"
	@echo "$(FRONTEND_IMAGE):$(TAG)"
	@echo "$(FRONTEND_IMAGE):$(REV)"

help: ## List the available targets
	@echo "Targets:"
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "} {printf "  %-16s %s\n", $$1, $$2}'
	@echo ""
	@echo "Variables (override on the command line):"
	@echo "  REGISTRY=$(REGISTRY)"
	@echo "  PROJECT=$(PROJECT)"
	@echo "  TAG=$(TAG)"
	@echo "  REV=$(REV)   (derived from git, not intended to be set)"
	@echo "  BACKEND_TARGET=$(BACKEND_TARGET)"
	@echo "  FRONTEND_TARGET=$(FRONTEND_TARGET)"
	@echo "  DOCKER=$(DOCKER)"
	@echo "  PLATFORM=$(PLATFORM)"
	@echo "  BUILD_ARGS=$(BUILD_ARGS)"
	@echo "  STACK=$(STACK)"
	@echo "  STACK_FILE=$(STACK_FILE)"
	@echo "  DEPLOY_FLAGS=$(DEPLOY_FLAGS)"
