# Builds the production container images and publishes them to a registry.
#
# Local development does not use this file — `docker compose up --build` selects
# the `dev` stage of each Dockerfile and is unaffected by anything here.
#
# Every variable is overridable on the command line:
#   make push
#   make push TAG=v1.2.3
#   make build REGISTRY=localhost:5000 PLATFORM=linux/amd64
#   make push BUILD_ARGS='--build-arg SERVER_API_BASE_URL=http://backend:8000'

REGISTRY        ?= direct:5000
PROJECT         ?= blueskies
TAG             ?= latest
DOCKER          ?= docker
PLATFORM        ?=
BUILD_ARGS      ?=
BACKEND_TARGET  ?= prod
FRONTEND_TARGET ?= prod

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

# Expands to nothing unless PLATFORM is set.
PLATFORM_FLAG := $(if $(strip $(PLATFORM)),--platform $(strip $(PLATFORM)),)

.DEFAULT_GOAL := help
.PHONY: help build build-backend build-frontend push push-backend push-frontend clean print-images

## --- build ------------------------------------------------------------------

# --target is passed explicitly rather than relying on the last stage winning,
# so appending a stage to a Dockerfile cannot silently change what is published.
# Both tags come from one build, which guarantees they denote the same image.

build-backend: ## Build the backend image (serves backend, celery and celery-beat)
	$(DOCKER) build $(PLATFORM_FLAG) $(BUILD_ARGS) \
		--target $(BACKEND_TARGET) \
		-t $(BACKEND_IMAGE):$(TAG) \
		-t $(BACKEND_IMAGE):$(REV) \
		./backend

build-frontend: ## Build the frontend image (Next.js standalone server)
	$(DOCKER) build $(PLATFORM_FLAG) $(BUILD_ARGS) \
		--target $(FRONTEND_TARGET) \
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
