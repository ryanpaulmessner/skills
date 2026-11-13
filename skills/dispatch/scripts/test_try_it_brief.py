"""Keep try-it handoff slots in the brief coordinators fill."""
from pathlib import Path
import unittest


class TryItBriefTest(unittest.TestCase):
    def test_builder_receives_preview_and_walkthrough_handoff_slots(self):
        skill = Path(__file__).parents[1] / "SKILL.md"
        brief = skill.read_text().split("```markdown", 1)[1].split("```", 1)[0]
        browser = brief.split("## Browser checks", 1)[1].split("## Build loop", 1)[0]
        report = brief.split("## Report back", 1)[1]
        for required in ["FOREMAN_SESSION=try-it-<ticket> devserve up",
                         "builds/<ticket>/walkthrough.json", "seed", "walkthrough record",
                         "Leave the preview running"]:
            self.assertIn(required, browser)
        for required in ["## Try it", "unit", "owner", "URL", "JSON path",
                         "seed commands", "video path"]:
            self.assertIn(required, report)


if __name__ == "__main__":
    unittest.main()
