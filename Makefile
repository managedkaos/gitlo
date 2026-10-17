.PHONY: help init _init setup-testing all gitea forgejo gitlabce gitbucket

PYTHON ?= python3
SERVICE ?= all

help: ## Display available targets
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_-]+:.*## / {printf "\033[36m%-28s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

init: ## Save local testing credentials and SSH key settings
	@$(PYTHON) scripts/testing.py init

_init:
	@$(PYTHON) scripts/testing.py ensure

setup-testing: _init ## Upload an SSH key and create testing-123 repositories
	@$(PYTHON) scripts/testing.py setup --service "$(SERVICE)"

all: gitea forgejo gitlabce gitbucket ## Deploy all Git hosting services

gitea: _init ## Deploy Gitea to Kubernetes
	$(MAKE) -C gitea deploy

forgejo: _init ## Deploy Forgejo to Kubernetes
	$(MAKE) -C forgejo deploy

gitlabce: _init ## Deploy GitLab CE to Kubernetes
	@$(PYTHON) scripts/testing.py gitlab-secret
	$(MAKE) -C gitlab-ce deploy

gitbucket: _init ## Deploy GitBucket to Kubernetes
	$(MAKE) -C gitbucket deploy
