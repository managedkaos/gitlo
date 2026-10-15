.PHONY: all gitea forgejo gitlabce

all: gitea forgejo gitlabce

gitea:
	$(MAKE) -C gitea deploy

forgejo:
	$(MAKE) -C forgejo deploy

gitlabce:
	$(MAKE) -C gitlab-ce deploy
