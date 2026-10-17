.PHONY: help all deploy clean nuke

help: ## Display available targets
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_-]+:.*## / {printf "\033[36m%-28s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

all: deploy ## Deploy Forgejo to Kubernetes

deploy: ## Apply Forgejo Kubernetes resources
	kubectl apply -f namespace.yaml
	kubectl apply -f pvc.yaml
	kubectl apply -f deployment.yaml
	kubectl apply -f service.yaml

clean: ## Remove Forgejo deployment and service
	kubectl delete --ignore-not-found -f service.yaml
	kubectl delete --ignore-not-found -f deployment.yaml

nuke: ## Delete all Forgejo resources and data
	@read -p "Enter the name of the service to delete (all data will be deleted): " confirm; \
	if [ "$$confirm" = "forgejo" ]; then \
		kubectl delete --ignore-not-found --cascade=foreground -f service.yaml; \
		kubectl delete --ignore-not-found --cascade=foreground -f deployment.yaml; \
		kubectl delete --ignore-not-found -f pvc.yaml; \
		kubectl delete --ignore-not-found -f namespace.yaml; \
	else \
		echo "Confirmation failed. Aborting nuke."; \
		exit 1; \
	fi
