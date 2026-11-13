import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("preview-cleanup.py")


class PreviewCleanupTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=SCRIPT.parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "state.json"
        self.calls = self.root / "calls.jsonl"
        self.env = {**os.environ, "PATH": str(self.root), "STATE": str(self.state),
                    "CALLS": str(self.calls)}
        cli = self.root / "devserve"
        cli.write_text(f"#!{sys.executable}\n" + '''import json, os, pathlib, sys
state = pathlib.Path(os.environ["STATE"])
args = sys.argv[1:]
with open(os.environ["CALLS"], "a") as log:
    log.write(json.dumps(args) + "\\n")
if args == ["ls", "--json"]:
    if os.environ.get("FAIL_LIST"):
        sys.exit(4)
    print(state.read_text())
elif len(args) == 3 and args[0] == "down" and args[2] == "--drop-db":
    if os.environ.get("FAIL_DOWN"):
        sys.exit(5)
    data = json.loads(state.read_text())
    if not os.environ.get("KEEP_PREVIEW"):
        data["previews"] = [p for p in data["previews"] if p["unit"] != args[1]]
        state.write_text(json.dumps(data))
else:
    sys.exit(6)
''')
        cli.chmod(0o755)

    def seed(self, previews):
        self.state.write_text(json.dumps({"previews": previews, "main_units": [
            {"unit": "foreman-web.service", "owner": "build-one"}]}))

    def run_cleanup(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args],
                              env=self.env, capture_output=True, text=True)

    def commands(self):
        return [json.loads(line) for line in self.calls.read_text().splitlines()]

    def test_drops_all_exact_owner_previews_and_leaves_others_and_mains(self):
        other = {"unit": "devserve-other.service", "owner": "build-one-more"}
        self.seed([{"unit": "devserve-a.service", "owner": "build-one"}, other,
                   {"unit": "devserve-b.service", "owner": "build-one", "state": "failed"}])
        result = self.run_cleanup("build-one")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.state.read_text())["previews"], [other])
        self.assertEqual(self.commands(), [["ls", "--json"],
            ["down", "devserve-a.service", "--drop-db"],
            ["down", "devserve-b.service", "--drop-db"], ["ls", "--json"]])

    def test_build_cleanup_preserves_try_it_until_explicit_cleanup(self):
        preview = {"unit": "devserve-try.service", "owner": "try-it-sk-a1b"}
        self.seed([preview, {"unit": "devserve-build.service", "owner": "build-one"}])
        self.assertEqual(self.run_cleanup("build-one").returncode, 0)
        self.assertEqual(json.loads(self.state.read_text())["previews"], [preview])
        self.assertEqual(self.run_cleanup("try-it-sk-a1b").returncode, 0)
        self.assertEqual(json.loads(self.state.read_text())["previews"], [])

    def stub_foreman(self):
        repo = self.root / "ticket-repo"
        repo.mkdir()
        cli = self.root / "foreman"
        cli.write_text(f"#!{sys.executable}\n" + f'''import json, os, sys
args = sys.argv[1:]
repo = {str(repo)!r}
if args[:3] == ["doc", "path", "report"]:
    print(json.dumps({{"path": repo + "/builds/" + args[3] + "/report.md"}}))
elif args[0] == "show":
    assert os.getcwd() == repo
    ticket = args[1]
    if os.environ.get("WARN_FOREMAN"):
        print(json.dumps({{"warning": "offline"}}))
    elif "--overlay" in args and os.environ.get("WARN_OVERLAY"):
        print(json.dumps({{"warning": "offline"}}))
    elif "--overlay" in args:
        print(json.dumps({{"id": ticket, "stage": os.environ.get("BOARD_STAGE", "abandoned" if ticket == "fm-old" else "building")}}))
    else:
        print(json.dumps({{"id": ticket, "status": "closed" if ticket == "sk-closed" else "open"}}))
else:
    sys.exit(2)
''')
        cli.chmod(0o755)

    def test_list_stale_resolves_ticket_repo_and_never_removes(self):
        self.stub_foreman()
        rows = [{"unit": f"devserve-{ticket}.service", "owner": f"try-it-{ticket}"}
                for ticket in ["sk-closed", "fm-old", "sk-live"]]
        rows.append({"unit": "devserve-build.service", "owner": "build-one"})
        self.seed(rows)
        result = self.run_cleanup("--list-stale")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("devserve-sk-closed.service\ttry-it-sk-closed\tsk-closed\tticket closed", result.stdout)
        self.assertIn("devserve-fm-old.service\ttry-it-fm-old\tfm-old\tboard abandoned", result.stdout)
        self.assertNotIn("devserve-sk-live.service", result.stdout)
        self.assertEqual(json.loads(self.state.read_text())["previews"], rows)
        self.assertEqual(self.commands(), [["ls", "--json"]])

    def test_list_stale_reports_post_publication_stages(self):
        self.stub_foreman()
        self.seed([{"unit": "devserve-a.service", "owner": "try-it-sk-live"}])
        for stage in ["pr_open", "merged", "done"]:
            self.env["BOARD_STAGE"] = stage
            result = self.run_cleanup("--list-stale")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"board {stage}", result.stdout)
        self.assertTrue(all(command == ["ls", "--json"] for command in self.commands()))

    def test_list_stale_read_failure_is_unknown_not_empty(self):
        self.stub_foreman()
        self.seed([{"unit": "devserve-a.service", "owner": "try-it-sk-live"}])
        for key, value in [("WARN_FOREMAN", "1"), ("WARN_OVERLAY", "1"), ("BOARD_STAGE", "")]:
            self.env[key] = value
            result = self.run_cleanup("--list-stale")
            del self.env[key]
            self.assertEqual(result.returncode, 1)
            self.assertIn("status unknown", result.stderr)
            self.assertEqual(result.stdout, "")
        self.assertEqual(self.commands(), [["ls", "--json"]] * 3)

    def test_committed_preview_is_kept_without_unknown_status(self):
        self.stub_foreman()
        rows = [{"unit": "devserve-a.service", "owner": "try-it-sk-live"}]
        self.seed(rows)
        self.env["BOARD_STAGE"] = "committed"
        result = self.run_cleanup("--list-stale")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(self.state.read_text())["previews"], rows)
        self.assertEqual(self.commands(), [["ls", "--json"]])

    def test_owner_and_list_stale_are_mutually_exclusive(self):
        result = self.run_cleanup("try-it-sk-a1b", "--list-stale")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.calls.exists())

    def test_empty_owner_is_rejected_before_listing(self):
        self.seed([])
        result = self.run_cleanup("")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_malformed_listing_is_rejected_before_any_drop(self):
        for payload in ["not json", "{}", '{"previews": {}}',
                        '{"previews": [{"owner": "build-one", "unit": "devserve-a.service"}, {}]}']:
            with self.subTest(payload=payload):
                self.state.write_text(payload)
                self.calls.write_text("")
                result = self.run_cleanup("build-one")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.commands(), [["ls", "--json"]])

    def test_no_owned_previews_is_successful_and_repeatable(self):
        self.seed([])
        for _ in range(2):
            result = self.run_cleanup("build-one")
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(), [["ls", "--json"]] * 4)

    def test_failed_list_or_drop_or_remaining_preview_blocks_closeout(self):
        for failure in ["FAIL_LIST", "FAIL_DOWN", "KEEP_PREVIEW"]:
            with self.subTest(failure=failure):
                self.seed([{"unit": "devserve-a.service", "owner": "build-one"}])
                self.env[failure] = "1"
                result = self.run_cleanup("build-one")
                del self.env[failure]
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("keep the session window", result.stderr)
                self.assertEqual(len(json.loads(self.state.read_text())["previews"]), 1)

    def test_missing_devserve_blocks_closeout(self):
        (self.root / "devserve").unlink()
        result = self.run_cleanup("build-one")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("keep the session window", result.stderr)


if __name__ == "__main__":
    unittest.main()
