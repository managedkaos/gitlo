.PHONY: all deploy clean nuke

help: ## Display available targets
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_-]+:.*## / {printf "\033[36m%-28s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

all: deploy ## Deploy Gitea to Kubernetes

deploy: ## Apply Gitea Kubernetes resources
	kubectl apply -f namespace.yaml
	kubectl apply -f pvc.yaml
	kubectl apply -f deployment.yaml
	kubectl apply -f service.yaml

clean:
	kubectl delete --ignore-not-found -f service.yaml
	kubectl delete --ignore-not-found -f deployment.yaml

nuke:
	@read -p "Enter the name of the service to delete (all data will be deleted): " confirm; \
	if [ "$$confirm" = "gitea" ]; then \
		kubectl delete --ignore-not-found --cascade=foreground -f service.yaml; \
		kubectl delete --ignore-not-found --cascade=foreground -f deployment.yaml; \
		kubectl delete --ignore-not-found -f pvc.yaml; \
		kubectl delete --ignore-not-found -f namespace.yaml; \
	else \
		echo "Confirmation failed. Aborting nuke."; \
		exit 1; \
	fi
