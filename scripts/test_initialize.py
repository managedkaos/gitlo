"""Offline checks for credentials, repeat runs and API error handling."""

import contextlib
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

import initialize


KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest gitlo"
VALUES = {"GITLO_USERNAME": "tester", "GITLO_PASSWORD": "pass$word'\"\\",
          "GITLO_EMAIL": "tester@example.com", "GITLAB_TOKEN": "private-token",
          **{s.upper() + "_URL": "http://" + s + ".local" for s in initialize.SERVICES}}


class FakeAPI:
    def __init__(self, service):
        self.service = service
        self.keys = []
        self.repo = None
        self.writes = []

    def request(self, path, data=None, **kwargs):
        if path == "/user":
            return {"login": "tester", "username": "tester"}
        if path == "/user/keys":
            self.keys.append(data)
        elif path in ("/projects", "/user/repos"):
            self.repo = data
        elif path.startswith(("/projects/", "/repos/")):
            return self.repo
        else:
            raise AssertionError(path)
        self.writes.append((path, data))
        return data

    def pages(self, path):
        return self.keys


class TestingTests(unittest.TestCase):
    def test_credentials_roundtrip_and_private_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            initialize.save(path, VALUES)
            self.assertEqual(initialize.load(path), VALUES)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            initialize.save(path, {**VALUES, "GITLO_PASSWORD": "updated"})
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_invalid_credentials_rejected(self):
        for field, value in (("GITLO_USERNAME", "Test User"), ("GITLO_USERNAME", "test123"),
                             ("GITLO_PASSWORD", ""), ("GITLO_EMAIL", "missing-at")):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                initialize.validate({**VALUES, field: value})

    def test_shell_expressions_are_not_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text('GITLO_PASSWORD=$(touch should-not-exist)\n')
            with self.assertRaises(ValueError):
                initialize.load(path)

    def test_seed_is_repeatable_for_every_service(self):
        for service in initialize.SERVICES:
            with self.subTest(service=service):
                api = FakeAPI(service)
                with patch.object(initialize, "Client", return_value=api), \
                     patch.object(initialize, "gitbucket_key") as upload, \
                     contextlib.redirect_stdout(io.StringIO()):
                    initialize.seed(service, VALUES, KEY)
                    count = len(api.writes)
                    initialize.seed(service, VALUES, KEY + " new-comment")
                    self.assertEqual(len(api.writes), count)
                    self.assertEqual(api.repo["name"], "testing-123")
                    if service == "gitbucket":
                        self.assertEqual(upload.call_count, 2)
                    else:
                        self.assertEqual(len(api.keys), 1)

    def test_wrong_token_owner_cannot_seed_another_account(self):
        api = FakeAPI("gitlab")
        with patch.object(initialize, "Client", return_value=api), self.assertRaises(ValueError):
            initialize.seed("gitlab", {**VALUES, "GITLAB_USERNAME": "someoneelse"}, KEY)
        self.assertEqual(api.writes, [])

    def test_gitbucket_form_upload_and_repeat(self):
        class Web:
            def __init__(self):
                self.keys = ""
                self.uploads = 0

            def request(self, path, data=None, **kwargs):
                if path.endswith(".keys"):
                    return self.keys
                if data and "publicKey" in data:
                    self.keys = data["publicKey"]
                    self.uploads += 1
                return '<input type="hidden" name="csrf" value="test-token">'

        web = Web()
        with patch.object(initialize, "Client", return_value=web):
            initialize.gitbucket_key("http://local", "tester", "password", KEY)
            initialize.gitbucket_key("http://local", "tester", "password", KEY)
        self.assertEqual(web.uploads, 1)

    def test_api_errors_do_not_expose_response_secrets(self):
        client = initialize.Client("http://local")
        error = HTTPError("http://local/user", 401, "Unauthorized", {}, io.BytesIO(b"secret-password"))
        with patch.object(client.opener, "open", side_effect=error), self.assertRaises(ValueError) as caught:
            client.request("/user")
        self.assertNotIn("secret-password", str(caught.exception))

    def test_redirect_cannot_leak_credentials_to_another_origin(self):
        handler = initialize.SameOriginRedirect()
        request = Request("http://local/api", headers={"Authorization": "Basic secret"})
        with self.assertRaises(ValueError):
            handler.redirect_request(request, None, 302, "", {}, "http://other/api")

    def test_key_pagination(self):
        client = initialize.Client("http://local")
        with patch.object(client, "request", side_effect=[[{"key": KEY}] * 50, [{"key": "last"}]]) as request:
            self.assertEqual(len(client.pages("/user/keys")), 51)
            self.assertIn("page=2", request.call_args.args[0])

    def test_gitlab_secret_uses_stdin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize.save(root / ".env", VALUES)
            with patch.object(initialize, "ROOT", root), \
                 patch("sys.argv", ["scripts/initialize.py", "gitlab-secret"]), \
                 patch.object(initialize.subprocess, "run") as run, \
                 contextlib.redirect_stdout(io.StringIO()):
                run.return_value.returncode = 0
                initialize.main()
                args, kwargs = run.call_args
                self.assertEqual(args[0], ["kubectl", "apply", "-f", "-"])
                self.assertEqual(json.loads(kwargs["input"])["kind"], "Secret")
                self.assertNotIn(VALUES["GITLO_PASSWORD"], repr(args))

    def test_missing_gitlab_token_fails_before_any_service_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize.save(root / ".env", {**VALUES, "GITLAB_TOKEN": ""})
            with patch.object(initialize, "ROOT", root), \
                 patch("sys.argv", ["scripts/initialize.py", "setup"]), \
                 patch.object(initialize, "seed") as seed, self.assertRaises(ValueError):
                initialize.main()
            seed.assert_not_called()

    def test_ensure_does_not_prompt_when_config_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize.save(root / ".env", VALUES)
            with patch.object(initialize, "ROOT", root), \
                 patch("sys.argv", ["scripts/initialize.py", "ensure"]), \
                 patch.object(initialize, "initialize") as initialize_mock:
                initialize.main()
            initialize_mock.assert_not_called()

    def test_gitlab_url_render_preserves_other_configuration(self):
        template = (initialize.ROOT / "gitlab-ce/deployment.yaml").read_text()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "gitlab-ce").mkdir()
            path = root / "gitlab-ce/deployment.yaml"
            path.write_text(template)
            with patch.object(initialize, "ROOT", root), contextlib.redirect_stdout(io.StringIO()):
                initialize.configure_gitlab("http://gitlab.example.test:8080")
                rendered = path.read_text()
                self.assertIn('value: "http://gitlab.example.test:8080"', rendered)
                self.assertIn("external_url ENV.fetch('GITLAB_URL')", rendered)
                self.assertEqual(len(template.splitlines()), len(rendered.splitlines()))
                initialize.configure_gitlab("http://gitlab.example.test:8080")
                self.assertEqual(path.read_text(), rendered)

    def test_invalid_gitlab_url_does_not_change_manifest(self):
        for url in ("file:///tmp/config", "http://user:password@host", "http://host\nmalicious", "http://host?query"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                initialize.configure_gitlab(url)

    def test_missing_gitlab_url_marker_fails_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "gitlab-ce").mkdir()
            path = root / "gitlab-ce/deployment.yaml"
            path.write_text("unexpected manifest")
            with patch.object(initialize, "ROOT", root), self.assertRaises(ValueError):
                initialize.configure_gitlab("http://gitlab.local")
            self.assertEqual(path.read_text(), "unexpected manifest")


if __name__ == "__main__":
    unittest.main()
