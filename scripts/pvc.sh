#!/usr/bin/env bash
set -euo pipefail

scope=(--all-namespaces)
if [[ -n "${1:-}" ]]; then
    scope=(--namespace "$1")
fi
# Include namespace for filtering, then remove it from the displayed report
kubectl get pvc "${scope[@]}" \
    -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,VOLUME:.spec.volumeName |
    awk 'NR == 1 || $1 ~ /^(forgejo|gitbucket|gitea|gitlab-ce)$/ {
        sub(/^[^[:space:]]+[[:space:]]+/, "")
        print
    }'
