GITBUCKET_VERSION ?= 4.48.0

.PHONY: all deploy destroy

all: deploy

deploy:
	kubectl apply -f namespace.yaml
	kubectl apply -f deployment.yaml
	kubectl apply -f service.yaml

update-version:
	sed -i "s|gitbucket/gitbucket:.*|gitbucket/gitbucket:$(GITBUCKET_VERSION)|" deployment.yaml

destroy:
	@read -p "Enter the name of the service to destroy: " confirm; \
	if [ "$$confirm" = "gitbucket" ]; then \
		kubectl delete -f service.yaml; \
		kubectl delete -f deployment.yaml; \
		kubectl delete -f namespace.yaml; \
	else \
		echo "Confirmation failed. Aborting destroy."; \
		exit 1; \
	fi
