.PHONY: help pods pvc urls init _init configure-gitlab setup-testing all gitea forgejo gitlabce gitbucket

PYTHON ?= python3
SERVICE ?= all
NAMESPACE ?=

help: ## Display available targets
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_-]+:.*## / {printf "\033[36m%-28s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

pods: ## List Git hosting pod names and namespaces
	@bash scripts/pods.sh "$(NAMESPACE)"

pvc: ## List Git hosting PVC names and bound volumes
	@bash scripts/pvc.sh "$(NAMESPACE)"

urls: ## List Git hosting service DNS URLs and ports
	@$(PYTHON) scripts/service_urls.py --namespace "$(NAMESPACE)"

init: ## Save local testing credentials and SSH key settings
	@$(PYTHON) scripts/initialize.py init

_init:
	@$(PYTHON) scripts/initialize.py ensure

setup-testing: _init ## Upload an SSH key and create testing-123 repositories
	@$(PYTHON) scripts/initialize.py setup --service "$(SERVICE)"

configure-gitlab: _init ## Set the GitLab deployment URL from local settings
	@$(PYTHON) scripts/initialize.py gitlab-config

all: gitea forgejo gitlabce gitbucket ## Deploy all Git hosting services

gitea: _init ## Deploy Gitea to Kubernetes
	$(MAKE) -C gitea deploy

forgejo: _init ## Deploy Forgejo to Kubernetes
	$(MAKE) -C forgejo deploy

gitlabce: _init ## Deploy GitLab CE to Kubernetes
	@$(PYTHON) scripts/initialize.py gitlab-config
	@$(PYTHON) scripts/initialize.py gitlab-secret
	$(MAKE) -C gitlab-ce deploy

gitbucket: _init ## Deploy GitBucket to Kubernetes
	$(MAKE) -C gitbucket deploy
