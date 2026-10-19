"""Тесты сканера: python3 -m unittest discover -s tests"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import scan  # noqa: E402

BAD = HERE / "fixtures" / "bad"
GOOD = HERE / "fixtures" / "good"


def ids(res):
    return [f["id"] for f in res["findings"]]


class BadFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = scan.run([], BAD, home=False)
        cls.ids = ids(cls.res)

    def test_discovers_claude_md_and_skill(self):
        self.assertEqual(self.res["files"], 2)

    def test_block_a(self):
        for fid in ("A1", "A2", "A3", "A4"):
            self.assertIn(fid, self.ids, fid)

    def test_dead_paths(self):
        msgs = [f["message"] for f in self.res["findings"] if f["id"] == "C1"]
        self.assertTrue(any("docs/missing-guide.md" in m for m in msgs))
        self.assertTrue(any("scripts/deploy.sh" in m for m in msgs))

    def test_old_model(self):
        self.assertIn("C4", self.ids)

    def test_duplicates_inside_and_across_files(self):
        d1 = [f for f in self.res["findings"] if f["id"] == "D1"]
        self.assertGreaterEqual(len(d1), 2)
        self.assertTrue(any("SKILL.md" in f["message"] for f in d1))

    def test_long_example(self):
        self.assertIn("D2", self.ids)

    def test_critical_first(self):
        self.assertEqual(self.res["findings"][0]["severity"], "critical")


class GoodFixture(unittest.TestCase):
    def test_clean_file_has_no_findings(self):
        res = scan.run([str(GOOD)], GOOD, home=False)
        self.assertEqual(res["findings"], [], res["findings"])

    def test_keep_block_counted(self):
        res = scan.run([str(GOOD / "CLAUDE.md")], GOOD, home=False)
        self.assertEqual(res["kept"], 3)


class Output(unittest.TestCase):
    def test_markdown_renders(self):
        md = scan.to_md(scan.run([], BAD, home=False))
        self.assertIn("🔴", md)
        self.assertIn("[C1]", md)


if __name__ == "__main__":
    unittest.main()
