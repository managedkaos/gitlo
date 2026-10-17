# gitlo

Kubernetes manifests for running git servers locally.

## Persistence

Each service stores its data on a PersistentVolumeClaim (PVC) backed by the default `local-path` StorageClass. Data survives pod restarts and `make clean` cycles. Only `make nuke` wipes it.

| Service    | PVC(s)                              | Mount path(s)                              | Size        |
|------------|-------------------------------------|--------------------------------------------|-------------|
| gitea      | `gitea-data`                        | `/data`                                    | 5 Gi        |
| forgejo    | `forgejo-data`                      | `/data`                                    | 5 Gi        |
| gitbucket  | `gitbucket-data`                    | `/gitbucket-data` (`GITBUCKET_HOME`)       | 5 Gi        |
| gitlab-ce  | `gitlab-ce-config`, `gitlab-ce-data`| `/etc/gitlab`, `/var/opt/gitlab`           | 1 Gi, 20 Gi |

GitLab logs (`/var/log/gitlab`) and shared memory (`/dev/shm`, 256 Mi) use ephemeral `emptyDir` volumes and are not persisted.

### Workflow

```
make deploy   # creates namespace + PVC + Deployment + Service (PVC re-used on subsequent runs)
make clean    # deletes Service and Deployment only; namespace and PVC are kept, data is intact
make nuke     # prompts for the service name, then deletes everything including the PVC and namespace
```

`make deploy` is idempotent: running it after `make clean` re-attaches the existing PVC so all data is preserved (no wizard, no re-initialisation).

> **Note:** Data lives on the single OrbStack node. Resetting or recreating the OrbStack cluster loses all data. Any backup requires separate tooling.

### GitLab initial root password

The initial root password is written to `/etc/gitlab/initial_root_password` on first boot. Because `/etc/gitlab` is now on the persistent `gitlab-ce-config` PVC, that file survives `make clean` + `make deploy` until GitLab deletes it (typically 24 hours after first boot).

### GitLab `external_url` precedence

`GITLAB_OMNIBUS_CONFIG` is evaluated on every start and its `external_url` value is written into `gitlab.rb` **only if the file does not already set it**. A hand-edited `gitlab.rb` on the persistent `/etc/gitlab` volume therefore takes precedence after the first `gitlab-ctl reconfigure`. The `GITLAB_OMNIBUS_CONFIG` value in `deployment.yaml` acts as the bootstrap default.

## forgejo

- Initally abandoned Forgejo due to the service not starting. Its working now.

## gitea

- Ran out of the box with no changes.
- Interface is snappy and responsive.
- Created a user with no issues.
- Added an SSH key.
- Clone a repo with no issues. Pushed a change with no issues.

## gitlab-ce

- Took some time to boot but the site came up.
- Created a user but needed to verify from admin account to enable the user.
- Had to get the admin password from the logs:

```bash
kubectl exec -n gitlab-ce -it $(kubectl get pods -n gitlab-ce -o jsonpath='{.items[0].metadata.name}') -- /bin/bash
```

Once in the pod, run:

```bash
cat /etc/gitlab/initial_root_password
```

- Logged in as admin and validated the user account.
- Had to set the URL to the k8s domain:

```bash
kubectl exec -n gitlab-ce -it $(kubectl get pods -n gitlab-ce -o jsonpath='{.items[0].metadata.name}') -- /bin/bash
```

Once in the pod, run:

```bash
vi /etc/gitlab/gitlab.rb
```

Set the value for `external_url` to the k8s domain:

```bash
external_url 'http://gitlab-ce.gitlab-ce.svc.cluster.local'
```

Then run:

```bash
gitlab-ctl reconfigure
gitlab-ctl restart
```
