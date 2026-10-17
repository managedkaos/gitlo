#!/usr/bin/env python3
"""Initialize local settings and seed test repositories using the standard library."""

import argparse
import base64
import getpass
from html.parser import HTMLParser
import http.cookiejar
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPCookieProcessor, HTTPRedirectHandler

ROOT = Path(__file__).resolve().parent.parent
SERVICES = ("gitea", "forgejo", "gitbucket", "gitlab")


def load(path):
    values = {}
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            name, value = line.split("=", 1)
            values[name.strip()] = json.loads(value)
            if not isinstance(values[name.strip()], str):
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError(f"Invalid setting at {path.name}:{number}; use JSON string quoting") from None
    return values


def validate(values):
    if not re.fullmatch(r"[a-z]+", values.get("GITLO_USERNAME", "")):
        raise ValueError("Username must be one word containing only lowercase letters")
    if not values.get("GITLO_PASSWORD"):
        raise ValueError("Password cannot be empty")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+", values.get("GITLO_EMAIL", "")):
        raise ValueError("Enter a valid email address")


def save(path, values):
    # Atomic replacement avoids exposing a partially written credentials file
    fd, name = tempfile.mkstemp(prefix=".gitlo-env-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            for key, value in values.items():
                stream.write(f"{key}={json.dumps(value)}\n")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def initialize(path):
    values = load(ROOT / "env_example.txt")
    if path.exists():
        values.update(load(path))
    for key, label in (("GITLO_USERNAME", "Username (lowercase letters)"),
                       ("GITLO_EMAIL", "Email address"),
                       ("SSH_PUBLIC_KEY", "SSH public key path")):
        values[key] = input(f"{label} [{values[key]}]: ").strip() or values[key]
    password = getpass.getpass("Password (blank keeps saved password): ")
    if password:
        if password != getpass.getpass("Confirm password: "):
            raise ValueError("Passwords do not match")
        values["GITLO_PASSWORD"] = password
    token = getpass.getpass("GitLab personal access token, api scope (blank keeps saved token): ")
    if token:
        values["GITLAB_TOKEN"] = token
    validate(values)
    save(path, values)
    print("Saved .env with permissions 0600; existing service accounts are unchanged")


class SameOriginRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(req.full_url)[:2] != urlsplit(newurl)[:2]:
            raise ValueError("Refusing to send credentials through a cross-origin redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Client:
    def __init__(self, url, headers=None):
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username:
            raise ValueError("Service URL must be an HTTP(S) URL without credentials")
        self.url = url.rstrip("/")
        self.headers = headers or {}
        self.opener = build_opener(SameOriginRedirect(), HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, path, data=None, form=False, missing=False, raw=False):
        headers = dict(self.headers)
        body = None
        if data is not None:
            body = (urlencode(data) if form else json.dumps(data)).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
            if form:
                headers["Referer"] = self.url + path
        try:
            with self.opener.open(Request(self.url + path, body, headers), timeout=30) as response:
                text = response.read().decode()
                if raw:
                    return text
                try:
                    return json.loads(text) if text else None
                except ValueError:
                    raise ValueError("Expected an API JSON response; check the service URL and authentication") from None
        except HTTPError as error:
            error.close()
            if error.code == 404 and missing:
                return None
            # Response bodies may contain credentials; do not print them
            raise ValueError(f"HTTP {error.code} for {path}; check credentials, permissions and service readiness") from None
        except URLError:
            raise ValueError("Cannot reach service; check its URL, DNS and readiness") from None

    def pages(self, path):
        result = []
        page = 1
        while True:
            separator = "&" if "?" in path else "?"
            items = self.request(f"{path}{separator}page={page}&limit=50&per_page=50")
            if not isinstance(items, list):
                raise ValueError("Expected a paginated API list")
            result.extend(items)
            if len(items) < 50:
                return result
            page += 1


class HiddenFields(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.fields = {}
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("type") == "hidden" and attrs.get("name"):
            self.fields[attrs["name"]] = attrs.get("value", "")


def key_identity(key):
    return key.split()[:2]


def gitbucket_key(url, username, password, key):
    # GitBucket 4.48 has no REST endpoint for SSH keys; use its settings form
    client = Client(url)
    fields = HiddenFields(client.request("/signin", raw=True)).fields
    client.request("/signin", {**fields, "userName": username, "password": password}, form=True, raw=True)
    settings = f"/{quote(username, safe='')}/_ssh"
    client.request(settings, raw=True)
    keys_path = f"/{quote(username, safe='')}.keys"
    if any(key_identity(line) == key_identity(key) for line in client.request(keys_path, raw=True).splitlines()):
        return
    fields = HiddenFields(client.request(settings, raw=True)).fields
    client.request(settings, {**fields, "title": "gitlo-testing", "publicKey": key}, form=True, raw=True)
    if not any(key_identity(line) == key_identity(key) for line in client.request(keys_path, raw=True).splitlines()):
        raise ValueError("GitBucket SSH-key upload did not succeed; check sign-in and key validity")


def seed(service, values, key):
    prefix = service.upper()
    username = values.get(prefix + "_USERNAME", values["GITLO_USERNAME"])
    password = values.get(prefix + "_PASSWORD", values["GITLO_PASSWORD"])
    url = values[prefix + "_URL"]
    if service == "gitlab":
        client = Client(url + "/api/v4", {"PRIVATE-TOKEN": values["GITLAB_TOKEN"]})
    else:
        auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        client = Client(url + ("/api/v3" if service == "gitbucket" else "/api/v1"),
                        {"Authorization": "Basic " + auth})
    user = client.request("/user")
    if user.get("username", user.get("login")) != username:
        raise ValueError("Authenticated user does not match the configured username")
    if service == "gitbucket":
        gitbucket_key(url, username, password, key)
    else:
        if not any(key_identity(item["key"]) == key_identity(key) for item in client.pages("/user/keys")):
            client.request("/user/keys", {"title": "gitlo-testing", "key": key})
    repository = quote(username + "/testing-123", safe="" if service == "gitlab" else "/")
    path = ("/projects/" if service == "gitlab" else "/repos/") + repository
    if client.request(path, missing=True) is None:
        if service == "gitlab":
            client.request("/projects", {"name": "testing-123", "path": "testing-123", "visibility": "private"})
        else:
            client.request("/user/repos", {"name": "testing-123", "private": True, "auto_init": False})
    if client.request(path, missing=True) is None:
        raise ValueError("Repository creation could not be verified")
    print(f"{service}: SSH key present; {username}/testing-123 ready")


def configure_gitlab(url):
    parsed = urlsplit(url)
    if (parsed.scheme not in ("http", "https") or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or any(c.isspace() for c in url)):
        raise ValueError("GITLAB_URL must be an HTTP(S) URL without credentials, query or fragment")
    path = ROOT / "gitlab-ce/deployment.yaml"
    original = path.read_text()
    updated, count = re.subn(
        r"(?m)^(            - name: GITLAB_URL\n              value: )[^\n]*$",
        lambda match: match[1] + json.dumps(url), original)
    if count != 1:
        raise ValueError("Expected exactly one GITLAB_URL value in the GitLab deployment")
    if updated != original:
        path.write_text(updated)
    print("GitLab deployment URL synchronized from .env")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "ensure", "setup", "gitlab-secret", "gitlab-config"))
    parser.add_argument("--service", choices=("all",) + SERVICES, default="all")
    args = parser.parse_args()
    path = ROOT / ".env"
    if args.command == "init" or (args.command == "ensure" and not path.exists()):
        initialize(path)
        return
    if not path.exists():
        raise ValueError("Run make init first")
    values = load(path)
    validate(values)
    if args.command == "ensure":
        return
    if args.command == "gitlab-config":
        configure_gitlab(values["GITLAB_URL"])
        return
    if args.command == "gitlab-secret":
        subprocess.run(["kubectl", "apply", "-f", str(ROOT / "gitlab-ce/namespace.yaml")], check=True)
        password = values.get("GITLAB_ROOT_PASSWORD") or values["GITLO_PASSWORD"]
        secret = {"apiVersion": "v1", "kind": "Secret", "metadata": {
            "name": "gitlo-bootstrap", "namespace": "gitlab-ce"},
            "type": "Opaque", "data": {"root-password": base64.b64encode(password.encode()).decode()}}
        # Send credentials through stdin rather than process arguments or a file
        result = subprocess.run(["kubectl", "apply", "-f", "-"], input=json.dumps(secret),
                                text=True, capture_output=True)
        if result.returncode:
            raise ValueError("Could not apply GitLab bootstrap Secret; check kubectl context and permissions")
        print("GitLab bootstrap Secret configured (fresh databases only)")
        return
    services = SERVICES if args.service == "all" else (args.service,)
    if "gitlab" in services and not values.get("GITLAB_TOKEN"):
        raise ValueError("Set GITLAB_TOKEN to your user's personal access token with api scope in .env")
    key = Path(values["SSH_PUBLIC_KEY"]).expanduser().read_text().strip()
    parts = key.split()
    if len(key.splitlines()) != 1 or len(parts) < 2 or not parts[0].startswith(("ssh-", "ecdsa-")):
        raise ValueError("SSH_PUBLIC_KEY must reference a single OpenSSH public key")
    try:
        base64.b64decode(parts[1], validate=True)
    except ValueError:
        raise ValueError("SSH public key has invalid base64 data") from None
    failures = []
    for service in services:
        try:
            seed(service, values, key)
        except (ValueError, OSError) as error:
            failures.append(service)
            print(f"{service}: {error}", file=sys.stderr)
    if failures:
        raise ValueError("Setup incomplete for: " + ", ".join(failures))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, EOFError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
