.PHONY: help all deploy destroy

help: ## Display available targets
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_-]+:.*## / {printf "\033[36m%-28s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

all: deploy ## Deploy Forgejo to Kubernetes

deploy: ## Apply Forgejo Kubernetes resources
	kubectl apply -f namespace.yaml
	kubectl apply -f deployment.yaml
	kubectl apply -f service.yaml

destroy: ## Delete Forgejo resources after confirmation
	@read -p "Enter the name of the service to destroy: " confirm; \
	if [ "$$confirm" = "forgejo" ]; then \
		kubectl delete -f service.yaml; \
		kubectl delete -f deployment.yaml; \
		kubectl delete -f namespace.yaml; \
	else \
		echo "Confirmation failed. Aborting destroy."; \
		exit 1; \
	fi
