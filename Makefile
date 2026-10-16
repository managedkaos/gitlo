.PHONY: all gitea forgejo gitlabce gitbucket

all: gitea forgejo gitlabce gitbucket

gitea:
	$(MAKE) -C gitea deploy

forgejo:
	$(MAKE) -C forgejo deploy

gitlabce:
	$(MAKE) -C gitlab-ce deploy

gitbucket:
	$(MAKE) -C gitbucket deploy
