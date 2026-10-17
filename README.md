# gitlo

Kubernetes manifests for running git servers locally.

## CLI listings

```bash
make pods                       # Git hosting pod namespaces and names
make urls                       # service DNS endpoints, including SSH ports
make pvc                        # PVC names and bound volumes for Git services
make pods NAMESPACE=gitbucket    # restrict a listing to one namespace
make urls NAMESPACE=gitbucket
make pvc NAMESPACE=gitbucket
```

All three commands use the current `kubectl` context and display only the `forgejo`,
`gitbucket`, `gitea`, and `gitlab-ce` namespaces. `NAMESPACE` further restricts
that selection. They do not require `.env`. Each listing makes one Kubernetes API query. `make urls`
uses Service ports rather than container ports and labels HTTP, HTTPS, SSH, and
other TCP/UDP endpoints. These are cluster DNS addresses; host access requires
OrbStack DNS integration or another route into the cluster. The listing does not
check application readiness or whether SSH is enabled, and does not show ingress
or externally advertised URLs.

## Testing setup

Use Python 3 (standard library only) and `kubectl` for the automation:

```bash
make init             # prompt for username, password, email, public key and GitLab token
make all              # deploy services; initialize .env first if it is missing
make setup-testing    # upload your public key and create testing-123 on every service
```

`make init` writes an ignored `.env` with permissions `0600`. The username must
contain only lowercase letters; use the same value for account names and display
names during manual signup. The default public key is `~/.ssh/id_ed25519.pub`.
Only the public key is read. Settings use JSON string quoting as shown in
[env_example.txt](env_example.txt); `.env` is read as data, never executed by a shell
or included by Make. Running `make init` again preserves saved settings when you
leave a prompt blank. It does not change existing accounts or passwords.

For existing accounts, enter their current credentials. If credentials differ
between services, set the per-service overrides shown in `env_example.txt`.
Create a personal access token with `api` scope from **your GitLab user account**
and enter it at the hidden token prompt (or set `GITLAB_TOKEN` in `.env`). GitLab
API calls use this token; the other services use username/password authentication.
Setup verifies the authenticated username before creating anything.

Accounts, initial web setup, and GitLab user approval remain manual. Gitea and
Forgejo offer CLI user creation rather than a shared initial-user environment
variable. GitBucket retains its own root bootstrap flow. For a fresh GitLab
database, top-level `make gitlabce` (also part of `make all`) creates a Kubernetes
Secret and supplies `GITLAB_ROOT_PASSWORD`, defaulting to `GITLO_PASSWORD`. You
can set a separate `GITLAB_ROOT_PASSWORD` in `.env`. GitLab's initial administrator
is still named `root`; create your personal account after logging in. The setting
does not reset passwords in an existing database. Deploying directly from the
GitLab subdirectory skips Secret provisioning and uses the existing Secret, if any.

Run testing setup after finishing web configuration and waiting for each service
to accept API requests. It creates a private, empty `testing-123` repository in
your personal namespace and skips existing repositories and matching SSH keys.
It leaves existing repository contents and settings intact. GitBucket 4.48 lacks
an SSH-key REST endpoint, so its upload uses a cookie-authenticated settings form
and verifies the result through the user's public key listing.

```bash
make setup-testing SERVICE=gitea  # also forgejo, gitbucket, or gitlab
```

Override service URLs in `.env` if OrbStack service DNS is unavailable from your
host. For example, port-forward a service and set its URL to the local HTTP port.
Use trusted local URLs for these local test instances. On failure, setup reports
the service, continues with the others, and exits unsuccessfully; fix the reported
problem and rerun it. Credentials and a GitLab token are required before running
setup for all services. Uploading a key does not enable GitBucket's SSH server;
enable it in GitBucket's system settings before testing SSH clone/push.

Root deployment targets reuse `.env` without prompting on subsequent runs. Direct
subdirectory deployment targets keep their existing behavior. Initialization and
deployment do not automatically run testing setup.

Offline automation checks: `python3 -m unittest discover -s scripts -p 'test_*.py'`.

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

Top-level `make gitlabce` (also part of `make all`) copies `GITLAB_URL` from `.env`
into the `GITLAB_URL` container environment entry in `gitlab-ce/deployment.yaml`
before deploying. `GITLAB_OMNIBUS_CONFIG` reads that value with
`external_url ENV.fetch('GITLAB_URL')`. To update the manifest without deploying,
run `make configure-gitlab`. Changing the manifest's environment value triggers a
new pod when applied. Direct subdirectory deployment uses the last rendered value.

GitLab evaluates `GITLAB_OMNIBUS_CONFIG` before `/etc/gitlab/gitlab.rb`; it does
not write these settings to that file. An explicit `external_url` in the persisted
`gitlab.rb` overrides the environment configuration. Remove or comment out that
old line once to let `.env` control the URL, then run `make gitlabce`.
See [GitLab container configuration](https://docs.gitlab.com/install/docker/configuration/).

`GITLAB_URL` is now both the advertised GitLab URL and the testing API base URL.
Use a canonical URL reachable by your host and clients. Custom ports or HTTPS
also require matching Service/listener/TLS configuration; this target only
synchronizes the URL.

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
