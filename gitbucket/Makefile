GITBUCKET_VERSION ?= 4.48.0

.PHONY: help all deploy destroy

help: ## Display available targets
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_-]+:.*## / {printf "\033[36m%-28s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

all: deploy ## Deploy GitBucket to Kubernetes

deploy: ## Apply GitBucket Kubernetes resources
	kubectl apply -f namespace.yaml
	kubectl apply -f deployment.yaml
	kubectl apply -f service.yaml

update-version: ## Set the GitBucket image to GITBUCKET_VERSION
	sed -i "s|gitbucket/gitbucket:.*|gitbucket/gitbucket:$(GITBUCKET_VERSION)|" deployment.yaml

destroy: ## Delete GitBucket resources after confirmation
	@read -p "Enter the name of the service to destroy: " confirm; \
	if [ "$$confirm" = "gitbucket" ]; then \
		kubectl delete -f service.yaml; \
		kubectl delete -f deployment.yaml; \
		kubectl delete -f namespace.yaml; \
	else \
		echo "Confirmation failed. Aborting destroy."; \
		exit 1; \
	fi
