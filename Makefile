# Variables
DOCKER_REGISTRY=ghcr.io/gatecoin
MICROCOIN_IMAGE=$(DOCKER_REGISTRY)/gatecoin-microcoin
VERSION=latest

# Build Docker images

build-microcoin:
	@echo "Building MICROCOIN Docker image: $(MICROCOIN_IMAGE):$(VERSION)..."
	docker build -t $(MICROCOIN_IMAGE):$(VERSION) ./microcoin
	@echo "MICROCOIN Docker image built successfully: $(MICROCOIN_IMAGE):$(VERSION)"

push-microcoin:
	@echo "Pushing MICROCOIN Docker image: $(MICROCOIN_IMAGE):$(VERSION)..."
	docker push $(MICROCOIN_IMAGE):$(VERSION)
	@echo "MICROCOIN Docker image pushed successfully: $(MICROCOIN_IMAGE):$(VERSION)"

# Build all images
build-all: build-web build-microcoin build-sandbox

# Push all images
push-all: push-web push-microcoin push-sandbox

build-push-microcoin: build-microcoin push-microcoin

# Build and push all images
build-push-all: build-all push-all
	@echo "All Docker images have been built and pushed."

# Phony targets
.PHONY: build-microcoin push-microcoin build-all push-all build-push-all