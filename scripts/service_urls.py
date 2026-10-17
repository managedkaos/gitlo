#!/usr/bin/env python3
"""List Service DNS endpoints without requiring local credentials in .env."""

import argparse
import json
import subprocess
import sys


def rows(items):
    for service in sorted(items, key=lambda item: (item["metadata"]["namespace"], item["metadata"]["name"])):
        name = service["metadata"]["name"]
        namespace = service["metadata"]["namespace"]
        if namespace not in {"forgejo", "gitbucket", "gitea", "gitlab-ce"}:
            continue
        spec = service["spec"]
        host = spec.get("externalName") or f"{name}.{namespace}.svc.cluster.local"
        for port in spec.get("ports", []):
            label = port.get("name", "")
            protocol = port.get("protocol", "TCP").lower()
            scheme = protocol
            if protocol == "tcp":
                scheme = next((s for s in ("https", "http", "ssh")
                               if label == s or label.startswith(s + "-")), protocol)
                if scheme == "tcp":
                    scheme = {80: "http", 443: "https", 22: "ssh"}.get(port["port"], protocol)
            suffix = "" if (scheme, port["port"]) in (("http", 80), ("https", 443)) else f':{port["port"]}'
            yield namespace, name, label or str(port["port"]), f"{scheme}://{host}{suffix}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--namespace", default="")
    args = parser.parse_args()
    scope = ["--namespace", args.namespace] if args.namespace else ["--all-namespaces"]
    result = subprocess.run(["kubectl", "get", "services", *scope, "-o", "json"],
                            stdout=subprocess.PIPE, text=True)
    if result.returncode:
        return result.returncode
    table = [("NAMESPACE", "SERVICE", "PORT", "SERVICE DNS URL"), *rows(json.loads(result.stdout)["items"])]
    widths = [max(len(row[index]) for row in table) for index in range(3)]
    for row in table:
        print("  ".join(value.ljust(width) for value, width in zip(row[:3], widths)) + "  " + row[3])
    if len(table) == 1:
        print("No service ports found")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
