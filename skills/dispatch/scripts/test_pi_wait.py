"""pi-wait against a fake tmux whose pane text is a file the test appends to."""
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import time
import unittest

SCRIPT = Path(__file__).with_name("pi-wait")
CODEX = "Error: Codex error: The usage limit has been reached"


class PiWaitTest(unittest.TestCase):
    mode = []
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        md5sum = shutil.which("md5sum") or shutil.which("gmd5sum")
        if md5sum:
            (bin_dir / "md5sum").symlink_to(md5sum)
        self.pane = root / "pane"
        self.pane.write_text("")
        tmux = bin_dir / "tmux"
        tmux.write_text(f'''#!/usr/bin/env python3
import sys, os
if sys.argv[1] == "list-panes":
    if not os.path.exists({str(root / 'gone')!r}):
        print("%12 build" if "@build" in sys.argv[-1] else "%12")
elif sys.argv[1] == "list-windows":
    print("build")
elif sys.argv[1] == "capture-pane":
    expected = "%12" if os.environ.get("PANE_MODE") else ":build"
    if sys.argv[sys.argv.index("-t") + 1] != expected: sys.exit(2)
    sys.stdout.write(open({str(self.pane)!r}).read())
''')
        tmux.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{bin_dir}:/usr/bin:/bin", PI_WAIT_INTERVAL="0.1",
                        PI_WAIT_IDLE="600")

    def wait(self, *lines, before=()):
        self.write(*before)
        proc = subprocess.Popen(["bash", str(SCRIPT), *self.mode, "build", "BUILD DONE", "10"], env=self.env,
                                stdout=subprocess.PIPE, text=True)
        time.sleep(0.4)  # let pi-wait take its baseline before the session prints
        self.write(*lines)
        out, _ = proc.communicate(timeout=10)
        return proc.returncode, out.strip().splitlines()

    def write(self, *lines):
        with self.pane.open("a") as pane:
            for line in lines:
                pane.write(line + "\n")

    def test_provider_limit_after_start_exits_limited_with_the_line(self):
        code, out = self.wait("working", "  " + CODEX + "  ")
        self.assertEqual(code, 5)
        self.assertEqual(out, ["LIMITED", CODEX])

    def test_anthropic_extra_usage_refusal_is_a_limit(self):
        line = "Error: Third-party apps now draw from your extra usage"
        self.assertEqual(self.wait(line), (5, ["LIMITED", line]))

    def test_rate_limit_429_is_a_limit(self):
        line = "Error: 429 rate limit exceeded, retry later"
        self.assertEqual(self.wait(line), (5, ["LIMITED", line]))

    def test_limit_printed_before_the_wait_started_does_not_count(self):
        code, out = self.wait("BUILD DONE", before=[CODEX, "continue"])
        self.assertEqual((code, out), (0, ["DONE"]))

    def test_limit_words_outside_an_error_line_are_ignored(self):
        code, out = self.wait('  assert msg =~ "usage limit has been reached"', "BUILD DONE")
        self.assertEqual((code, out), (0, ["DONE"]))

    def test_done_beats_limited(self):
        self.assertEqual(self.wait(CODEX, "BUILD DONE"), (0, ["DONE"]))

    def test_trust_prompt_exits_blocked(self):
        code, out = self.wait(" Trust project folder?", " /home/me/dev/new-worktree", " → Trust",
                              "   Trust parent folder (/home/me/dev)")
        self.assertEqual(code, 6)
        self.assertEqual(out[0], "BLOCKED")
        self.assertIn("Trust project folder?", out[1])

    def test_the_prompt_quoted_in_text_is_not_blocked(self):
        code, out = self.wait('stops at pi\'s "Trust project folder?" prompt and waits', "BUILD DONE")
        self.assertEqual((code, out), (0, ["DONE"]))

    def test_screen_unchanged_for_the_idle_limit_exits_idle_with_last_lines(self):
        self.env["PI_WAIT_IDLE"] = "1"
        code, out = self.wait("working", "One gate remains: may I create a fixture commit?")
        self.assertEqual(code, 7)
        self.assertEqual(out[0], "IDLE")
        self.assertIn("One gate remains: may I create a fixture commit?", out)

    def test_a_changing_screen_is_not_idle(self):
        self.env["PI_WAIT_IDLE"] = "1"
        self.write("start")
        proc = subprocess.Popen(["bash", str(SCRIPT), *self.mode, "build", "BUILD DONE", "10"], env=self.env,
                                stdout=subprocess.PIPE, text=True)
        for i in range(12):  # keep printing for about 1.2 s, longer than the idle limit
            time.sleep(0.1)
            self.write(f"step {i}")
        self.write("BUILD DONE")
        out, _ = proc.communicate(timeout=10)
        self.assertEqual((proc.returncode, out.strip().splitlines()), (0, ["DONE"]))

    def test_done_beats_idle(self):
        self.env["PI_WAIT_IDLE"] = "1"
        self.assertEqual(self.wait("BUILD DONE"), (0, ["DONE"]))


class PiPaneWaitTest(PiWaitTest):
    mode = ["--pane"]

    def setUp(self):
        super().setUp()
        self.env["PANE_MODE"] = "1"

    def test_pane_disappearing_during_wait_is_gone(self):
        proc = subprocess.Popen(["bash", str(SCRIPT), "--pane", "build", "BUILD DONE", "10"],
                                env=self.env, text=True, stdout=subprocess.PIPE)
        time.sleep(.4)
        (self.pane.parent / "gone").touch()
        out, _ = proc.communicate(timeout=5)
        self.assertEqual((proc.returncode, out.strip()), (2, "GONE"))

    def test_ambiguous_tag_is_not_captured(self):
        tmux = self.pane.parent / "bin" / "tmux"
        tmux.write_text('#!/bin/sh\nprintf "%s\\n" "%12 build" "%13 build"\n')
        result = subprocess.run(["bash", str(SCRIPT), "--pane", "build", "BUILD DONE", "1"],
                                env=self.env, text=True, capture_output=True)
        self.assertEqual((result.returncode, result.stdout.strip()), (2, "GONE"))

    def test_gone_pane_does_not_wait_on_coordinator_window(self):
        (self.pane.parent / "gone").touch()
        result = subprocess.run(["bash", str(SCRIPT), "--pane", "build", "BUILD DONE", "1"],
                                env=self.env, text=True, capture_output=True)
        self.assertEqual((result.returncode, result.stdout.strip()), (2, "GONE"))


if __name__ == "__main__":
    unittest.main()
