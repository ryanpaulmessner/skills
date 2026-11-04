"""Process-boundary tests; no real tmux, pi session, board or user config."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("pi-window")
SENDER = SCRIPT.parents[2] / "foreman/scripts/foreman-send"
ZSH = shutil.which("zsh") or "/usr/bin/zsh"
TIMEOUT = shutil.which("timeout")
UUID = "3f2b8c1e-9d4a-4e7b-a1c2-5d6e7f8a9b0c"

# Window launches run in place; the pane shows a pinned Bifrost footer for --model.
TMUX_RUNS_WINDOW = '''import os, subprocess, sys
args = sys.argv[1:]
if args[0] == "new-window":
    subprocess.run(args[-1], shell=True, cwd=args[args.index("-c") + 1], stdin=subprocess.DEVNULL)
if args[0] == "capture-pane": print("Bifrost · pinned provider/model")
'''
# Logs every call; split-window prints the new pane id.
TMUX_RECORDS = '''import json, os, sys
args = sys.argv[1:]
with open(os.environ["LOG"], "a") as f:
    f.write(json.dumps(["tmux", args]) + "\\n")
if args[0] == "split-window": print("%12")
'''
PI = '''import json, os, sys
with open(os.environ["LOG"], "a") as f:
    f.write(json.dumps(["pi", os.environ.get("FOREMAN_ACTOR"), os.environ.get("FOREMAN_SESSION"), sys.argv[1:], os.environ.get("FOREMAN_TICKETS"), os.environ.get("FOREMAN_PARENT")]) + "\\n")
'''
FOREMAN = '''import json, os, sys
with open(os.environ["LOG"], "a") as f:
    f.write(json.dumps(["foreman", os.environ.get("FOREMAN_ACTOR"), os.environ.get("FOREMAN_SESSION"), sys.argv[1:], os.getcwd()]) + "\\n")
sys.exit(int(os.environ.get("FOREMAN_EXIT", "0")))
'''


class PiWindowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        # Host tools the scripts need, kept off PATH for tests that remove them.
        self.tools = self.root / "tools"
        self.tools.mkdir()
        if TIMEOUT:
            (self.tools / "timeout").symlink_to(TIMEOUT)
        self.repo = self.root / "work tree"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "build"], cwd=self.repo, check=True)
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                        "commit", "-qm", "base", "--allow-empty"], cwd=self.repo, check=True)
        self.base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.repo, text=True).strip()
        self.brief = self.root / "brief.md"
        self.brief.write_text("Build this slice.\n")
        self.report = self.repo / "report.md"
        self.log = self.root / "events"
        # The caller is an epic coordinator: its FOREMAN_SESSION and pane are inherited.
        self.env = dict(os.environ, PATH=f"{self.bin}:{self.tools}:/usr/bin:/bin", TMUX="fake",
                        TMUX_PANE="%3", LOG=str(self.log), FOREMAN_ACTOR="inherited",
                        FOREMAN_SESSION="epic-coord")
        self.env.pop("FOREMAN_PARENT", None)
        self.executable("tmux", TMUX_RUNS_WINDOW)
        self.executable("zsh", f'import subprocess, sys\nsys.exit(subprocess.call([{ZSH!r}, "-f", "-c", sys.argv[-1]]))\n')
        self.executable("uuidgen", f"print({UUID.upper()!r})\n")
        self.executable("pi", PI)
        self.executable("foreman", FOREMAN)

    def executable(self, name, body):
        path = self.bin / name
        path.write_text("#!/usr/bin/python3\n" + body)
        path.chmod(0o755)

    def launch(self, *args, mode=()):
        return subprocess.run(["bash", str(SCRIPT), *mode, "slice", str(self.repo), str(self.brief), *args],
                              env=self.env, text=True, capture_output=True, timeout=20)

    def events(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def calls(self, kind, verb=()):
        return [e for e in self.events() if e[0] == kind and e[3][:len(verb)] == list(verb)]

    def dispatches(self):
        return self.calls("foreman", ["dispatch"])

    def test_pane_launch_tags_titles_and_records_exact_target(self):
        self.env["TMUX_PANE"] = "%7"
        self.executable("tmux", TMUX_RECORDS)
        result = self.launch("--bead", "sk-1", mode=["--pane"])
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [e[1] for e in self.events() if e[0] == "tmux"]
        split = next(c for c in calls if c[0] == "split-window")
        self.assertEqual(split[split.index("-t") + 1], "%7")
        self.assertIn(["set-option", "-p", "-t", "%12", "@build", "slice"], calls)
        self.assertIn(["select-pane", "-t", "%12", "-T", "slice"], calls)
        self.assertFalse(any(c[0] == "new-window" for c in calls))
        board = self.dispatches()[0][3]
        self.assertEqual(board[board.index("--window") + 1], "%12")
        self.assertIn("launched pi in pane 'slice' (%12)", result.stdout)

    def test_pane_build_records_name_pi_session_and_coordinator(self):
        self.env["TMUX_PANE"] = "%7"
        self.executable("tmux", TMUX_RECORDS)
        result = self.launch("--bead", "sk-1", "--", "-e", "/tmp/extension", mode=["--pane"])
        self.assertEqual(result.returncode, 0, result.stderr)
        split = next(e[1] for e in self.events() if e[0] == "tmux" and e[1][0] == "split-window")
        command = split[-1]
        self.assertIn(f'pi --name "slice" --session-id {UUID} -e /tmp/extension', command)
        self.assertIn("FOREMAN_SESSION=slice FOREMAN_PARENT=epic-coord ", command)
        self.assertIn('--harness pi --parent "$FOREMAN_PARENT"', command)
        [dispatch] = self.dispatches()
        self.assertEqual(dispatch[1:3], ["pi", "epic-coord"])
        self.assertEqual(dispatch[3][:8], ["dispatch", "sk-1", "--name", "slice", "--pi-session", UUID,
                                           "--coordinator", "epic-coord"])
        self.assertEqual(dispatch[3][dispatch[3].index("--window") + 1], "%12")
        self.assertNotIn("--session", dispatch[3])

    def test_window_build_starts_pi_with_the_dispatched_session_id(self):
        result = self.launch("--bead", "sk-1")
        self.assertEqual(result.returncode, 0, result.stderr)
        [register] = self.calls("foreman", ["session", "register"])
        self.assertEqual(register[3], ["session", "register", "--name", "slice", "--pane", "%3",
                                       "--workdir", str(self.repo.resolve()), "--harness", "pi",
                                       "--parent", "epic-coord"])
        [pi] = self.calls("pi")
        self.assertEqual(pi[3][:4], ["--name", "slice", "--session-id", UUID])
        self.assertEqual(pi[5], "epic-coord")
        [dispatch] = self.dispatches()
        self.assertEqual(dispatch[3][:8], ["dispatch", "sk-1", "--name", "slice", "--pi-session", UUID,
                                           "--coordinator", "epic-coord"])
        self.assertEqual(dispatch[3][dispatch[3].index("--window") + 1], "slice")

    def test_without_a_coordinator_the_build_still_records_its_own_identity(self):
        for inherited in (None, "slice"):
            with self.subTest(inherited=inherited):
                self.log.unlink(missing_ok=True)
                if inherited:
                    self.env["FOREMAN_SESSION"] = inherited
                else:
                    self.env.pop("FOREMAN_SESSION", None)
                result = self.launch("--bead", "sk-1")
                self.assertEqual(result.returncode, 0, result.stderr)
                [register] = self.calls("foreman", ["session", "register"])
                self.assertNotIn("--parent", register[3])
                [dispatch] = self.dispatches()
                self.assertIsNone(dispatch[2])
                self.assertEqual(dispatch[3][:6], ["dispatch", "sk-1", "--name", "slice", "--pi-session", UUID])
                self.assertNotIn("--coordinator", dispatch[3])
                self.assertEqual(self.calls("pi")[0][3][:4], ["--name", "slice", "--session-id", UUID])

    def test_unsafe_caller_session_is_not_a_coordinator(self):
        self.env["FOREMAN_SESSION"] = "two words"
        result = self.launch("--bead", "sk-1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("launching without a coordinator", result.stderr)
        self.assertNotIn("--coordinator", self.dispatches()[0][3])

    def test_session_flags_in_pi_args_are_respected(self):
        cases = ((("--session-id", "given-id"), "given-id"), (("--session-id=given-id",), "given-id"),
                 (("--continue",), None), (("--session", "abc"), None), (("-r",), None))
        for pi_args, recorded in cases:
            with self.subTest(pi_args=pi_args):
                self.log.unlink(missing_ok=True)
                result = self.launch("--bead", "sk-1", "--", *pi_args)
                self.assertEqual(result.returncode, 0, result.stderr)
                pi = self.calls("pi")[0][3]
                given = pi.count("--session-id") + sum(a.startswith("--session-id=") for a in pi)
                self.assertEqual(given, 1 if recorded else 0)
                self.assertNotIn(UUID, pi)
                args = self.dispatches()[0][3]
                if recorded:
                    self.assertEqual(args[args.index("--pi-session") + 1], recorded)
                else:
                    self.assertNotIn("--pi-session", args)

    def test_failed_uuid_refuses_before_launch(self):
        self.executable("uuidgen", "print('not-a-uuid')\n")
        result = self.launch("--bead", "sk-1")
        self.assertEqual(result.returncode, 2)
        self.assertIn("could not generate a pi session id", result.stderr)
        self.assertFalse(self.log.exists())

    def test_duplicate_pane_refuses_both_launch_modes(self):
        self.env["TMUX_PANE"] = "%7"
        self.executable("tmux", 'import sys\nif sys.argv[1] == "list-panes": print("%12 slice")\n')
        for mode in ([], ["--pane"]):
            result = self.launch("--bead", "sk-1", mode=mode)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("pane already exists", result.stderr)
            self.assertFalse(self.log.exists())

    def test_exports_identity_into_pi(self):
        result = self.launch("--model", "provider/model")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls("pi")[0], ["pi", "pi", "slice",
                         ["--name", "slice", "--session-id", UUID, "--model", "provider/model"], "",
                         "epic-coord"])

    def test_dispatches_each_ticket_after_launch_with_metadata(self):
        result = self.launch("--bead", "sk-1", "--bead", "sk-2", "--report", str(self.report),
                             "--", "--model", "provider/model", "-e", "/tmp/extension")
        self.assertEqual(result.returncode, 0, result.stderr)
        events = [e for e in self.events() if e[3][:1] != ["session"]]
        self.assertEqual([event[0] for event in events], ["pi", "foreman", "foreman"])
        self.assertEqual(events[0][4], "sk-1 sk-2")
        self.assertEqual(events[0][3], ["--name", "slice", "--session-id", UUID, "--model",
                                       "provider/model", "-e", "/tmp/extension"])
        for event, ticket in zip(events[1:], ["sk-1", "sk-2"]):
            self.assertEqual(event, ["foreman", "pi", "epic-coord", ["dispatch", ticket,
                "--name", "slice", "--pi-session", UUID, "--coordinator", "epic-coord",
                "--window", "slice", "--harness", "pi", "--model", "provider/model",
                "--workdir", str(self.repo), "--branch", "build", "--base", self.base,
                "--brief", str(self.brief), "--report", str(self.report)], str(self.repo)])

    def test_brief_path_is_literal_shell_data(self):
        self.brief = self.root / "brief 'with\" $dollars.md"
        self.brief.write_text("Quoted path works.\n")
        result = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.log.exists(), result.stderr)
        self.assertEqual(self.calls("pi")[0][3][-1], "Quoted path works.")

    def tracked_launch(self):
        return self.launch("--bead", "sk-1", "--bead", "sk-2", "--report", str(self.report))

    def test_missing_board_warns_once_and_still_launches(self):
        (self.bin / "foreman").unlink()
        result = self.tracked_launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([event[0] for event in self.events()], ["pi"])
        self.assertEqual(len(result.stderr.splitlines()), 1, result.stderr)
        self.assertIn("warning: foreman", result.stderr)

    def test_refused_or_failed_board_never_fails_launch_or_skips_next_ticket(self):
        for code in (3, 1, 127):
            with self.subTest(code=code):
                self.log.unlink(missing_ok=True)
                self.env["FOREMAN_EXIT"] = str(code)
                result = self.tracked_launch()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len(self.calls("pi")), 1)
                self.assertEqual(len(self.dispatches()), 2)
                self.assertIn("warning: foreman", result.stderr)

    def test_relative_report_and_pi_model_forms(self):
        for model_args in (("-m", "provider/model"), ("--model=provider/model",)):
            with self.subTest(model_args=model_args):
                self.log.unlink(missing_ok=True)
                result = self.launch("--bead", "sk-1", "--report", "reports/slice.md", "--", *model_args)
                self.assertEqual(result.returncode, 0, result.stderr)
                args = self.dispatches()[0][3]
                self.assertEqual(args[args.index("--model") + 1], "provider/model")
                self.assertEqual(args[args.index("--report") + 1], str(self.repo / "reports/slice.md"))

    def test_non_git_workdir_still_launches_with_honest_defaults(self):
        self.repo = self.root / "not-git"
        self.repo.mkdir()
        result = self.launch("--bead", "sk-1")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.dispatches()[0][3]
        for flag, expected in (("--branch", "unknown"), ("--base", "unknown"), ("--model", "default"),
                               ("--report", str(self.repo / "drafts/sessions/slice.md"))):
            self.assertEqual(args[args.index(flag) + 1], expected)

    def test_duplicate_window_never_launches_or_dispatches(self):
        self.executable("tmux", 'import sys\nif sys.argv[1] == "list-windows": print("slice")\n')
        result = self.tracked_launch()
        self.assertEqual(result.returncode, 1)
        self.assertIn("window already exists", result.stderr)
        self.assertFalse(self.log.exists())

    def test_report_refusal_cannot_prevent_done_marker_under_errexit(self):
        self.env["FOREMAN_EXIT"] = "3"
        result = subprocess.run(["bash", "-ec",
            'bash "$1" report sk-1 --path "$2"; echo "SLICE DONE"',
            "test", str(SENDER), str(self.report)], env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "SLICE DONE")
        self.assertIn("warning: foreman exited 3", result.stderr)
        self.assertEqual(self.events()[0][3], ["report", "sk-1", "--path", str(self.report)])

    def test_missing_timeout_skips_board_with_warning(self):
        self.env["PATH"] = str(self.bin)
        result = subprocess.run(["/bin/bash", str(SENDER), "progress", "sk-1", "green"],
                                env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("timeout unavailable", result.stderr)
        self.assertFalse(self.log.exists())

    def test_failed_tmux_launch_does_not_claim_dispatch(self):
        self.executable("tmux", 'import sys\nif sys.argv[1] == "new-window": sys.exit(1)\n')
        result = self.tracked_launch()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.log.exists())

    def test_hung_board_is_bounded_and_launch_survives(self):
        self.executable("foreman", "import time\ntime.sleep(60)\n")
        result = self.launch("--bead", "sk-1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.calls("pi")), 1)
        self.assertIn("warning: foreman", result.stderr)


if __name__ == "__main__":
    unittest.main()
