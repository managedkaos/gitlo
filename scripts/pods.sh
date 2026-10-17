#!/usr/bin/env bash
set -euo pipefail

# Keep only this project's namespaces and display the compact pod report
scope=(--all-namespaces)
if [[ -n "${1:-}" ]]; then
    scope=(--namespace "$1")
fi
kubectl get pods "${scope[@]}" \
    -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name |
    awk 'NR == 1 || $1 ~ /^(forgejo|gitbucket|gitea|gitlab-ce)$/'
