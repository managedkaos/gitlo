# gitlo

Kubernetes manifests for running git servers locally.

## forgejo

- Failed to load out of the box.
- Abandoning.

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
