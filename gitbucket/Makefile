GITBUCKET_VERSION ?= 4.48.0

.PHONY: all deploy

all: deploy

deploy:
	kubectl apply -f namespace.yaml
	kubectl apply -f deployment.yaml
	kubectl apply -f service.yaml

update-version:
	sed -i "s|gitbucket/gitbucket:.*|gitbucket/gitbucket:$(GITBUCKET_VERSION)|" deployment.yaml
