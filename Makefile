.PHONY: help all gitea forgejo gitlabce gitbucket

help: ## Display available targets
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_-]+:.*## / {printf "\033[36m%-28s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

all: gitea forgejo gitlabce gitbucket ## Deploy all Git hosting services

gitea: ## Deploy Gitea to Kubernetes
	$(MAKE) -C gitea deploy

forgejo: ## Deploy Forgejo to Kubernetes
	$(MAKE) -C forgejo deploy

gitlabce: ## Deploy GitLab CE to Kubernetes
	$(MAKE) -C gitlab-ce deploy

gitbucket: ## Deploy GitBucket to Kubernetes
	$(MAKE) -C gitbucket deploy
