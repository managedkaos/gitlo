GITBUCKET_VERSION ?= 4.48.0

.PHONY: all deploy clean nuke

all: deploy

deploy:
	kubectl apply -f namespace.yaml
	kubectl apply -f pvc.yaml
	kubectl apply -f deployment.yaml
	kubectl apply -f service.yaml

update-version:
	sed -i "s|gitbucket/gitbucket:.*|gitbucket/gitbucket:$(GITBUCKET_VERSION)|" deployment.yaml

clean:
	kubectl delete --ignore-not-found -f service.yaml
	kubectl delete --ignore-not-found -f deployment.yaml

nuke:
	@read -p "Enter the name of the service to delete (all data will be deleted): " confirm; \
	if [ "$$confirm" = "gitbucket" ]; then \
		kubectl delete --ignore-not-found --cascade=foreground -f service.yaml; \
		kubectl delete --ignore-not-found --cascade=foreground -f deployment.yaml; \
		kubectl delete --ignore-not-found -f pvc.yaml; \
		kubectl delete --ignore-not-found -f namespace.yaml; \
	else \
		echo "Confirmation failed. Aborting nuke."; \
		exit 1; \
	fi
