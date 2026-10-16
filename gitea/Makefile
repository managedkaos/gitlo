.PHONY: all deploy destroy

all: deploy

deploy:
	kubectl apply -f namespace.yaml
	kubectl apply -f deployment.yaml
	kubectl apply -f service.yaml

destroy:
	@read -p "Enter the name of the service to destroy: " confirm; \
	if [ "$$confirm" = "gitea" ]; then \
		kubectl delete -f service.yaml; \
		kubectl delete -f deployment.yaml; \
		kubectl delete -f namespace.yaml; \
	else \
		echo "Confirmation failed. Aborting destroy."; \
		exit 1; \
	fi
