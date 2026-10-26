"""Тесты сканера: python3 -m unittest discover -s tests"""
import sys
import tempfile
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

    def test_discovers_instruction_files(self):
        # CLAUDE.md, AGENTS.md и четыре SKILL.md под .claude/skills
        self.assertEqual(self.res["files"], 6)

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

    def by_id(self, fid):
        return [f for f in self.res["findings"] if f["id"] == fid]

    def test_e1_frontmatter(self):
        msgs = [(f["file"], f["message"]) for f in self.by_id("E1")]
        self.assertTrue(any("no-frontmatter" in f and "не начинается" in m for f, m in msgs), msgs)
        self.assertTrue(any("wrong-folder" in f and "description" in m for f, m in msgs), msgs)

    def test_e2_name(self):
        msgs = [f["message"] for f in self.by_id("E2")]
        self.assertTrue(any("kebab-case" in m for m in msgs), msgs)
        self.assertTrue(any("wrong-folder" in m for m in msgs), msgs)

    def test_e4_long_description(self):
        self.assertEqual(len(self.by_id("E4")), 1)

    def test_e6_missing_skill_file_in_code_block(self):
        e6 = self.by_id("E6")
        self.assertTrue(any("scripts/build_report.py" in f["message"] for f in e6), e6)
        # путь в `кавычках` уже найден как C1 — второй раз как E6 не дублируется
        self.assertFalse(any("references/template.md" in f["message"] for f in e6))
        self.assertTrue(any("references/template.md" in f["message"] for f in self.by_id("C1")))

    def test_e_checks_only_for_skill_md(self):
        for f in self.res["findings"]:
            if f["id"].startswith("E"):
                self.assertTrue(f["file"].endswith("SKILL.md"), f)

    def test_f1_secrets_masked(self):
        f1 = self.by_id("F1")
        self.assertEqual(len(f1), 4, f1)
        self.assertTrue(all(f["severity"] == "critical" for f in f1))
        text = " ".join(f["quote"] for f in f1)
        for secret in ("AKIAEXAMPLEEXAMPLE00", "ghp_FAKEFAKE", "sk-ant-FAKE", "FAKE-hunter2"):
            self.assertNotIn(secret, text)
        self.assertIn("AKIA…", text)

    def test_f2_pii_masked(self):
        f2 = self.by_id("F2")
        self.assertEqual(len(f2), 1, f2)
        self.assertEqual(f2[0]["severity"], "important")
        self.assertIn("почта", f2[0]["message"])
        self.assertIn("телефон", f2[0]["message"])
        self.assertNotIn("petrov.fake@company.ru", f2[0]["quote"])
        self.assertNotIn("000-00-00", f2[0]["quote"])

    def test_critical_first(self):
        self.assertEqual(self.res["findings"][0]["severity"], "critical")


class GoodFixture(unittest.TestCase):
    def test_clean_file_has_no_findings(self):
        res = scan.run([str(GOOD)], GOOD, home=False)
        self.assertEqual(res["findings"], [], res["findings"])

    def test_clean_skill_passes_e_checks(self):
        res = scan.run([str(GOOD / "skills")], GOOD, home=False)
        self.assertEqual(res["files"], 1)
        self.assertEqual(res["findings"], [])

    def test_keep_block_counted(self):
        res = scan.run([str(GOOD / "CLAUDE.md")], GOOD, home=False)
        self.assertEqual(res["kept"], 3)


class SecretPatterns(unittest.TestCase):
    """Шаблоны, которые не хранятся в фикстурах целиком: строка собирается в тесте."""

    def scan_text(self, text, name="CLAUDE.md"):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / name
            p.write_text(text, encoding="utf-8")
            return scan.run([str(p)], Path(d), home=False)["findings"]

    def test_slack_and_private_key(self):
        slack = "xo" + "xb-" + "0000-FAKE-EXAMPLE-token"
        pem = "-----BEGIN " + "RSA PRIVATE KEY-----"
        found = self.scan_text(f"Slack: {slack}\n\n{pem}\n")
        self.assertEqual([f["id"] for f in found], ["F1", "F1"], found)
        self.assertNotIn(slack, " ".join(f["quote"] for f in found))

    def test_placeholders_and_env_are_not_secrets(self):
        found = self.scan_text(
            'token = "<your-token>"\n\npassword: "${DB_PASSWORD}"\n\n'
            'key = os.environ["API_KEY"]\n\nВерсия 1.1.0, дата 2026-10-26, сборка 81234567.\n'
            "Пишите на support@example.com или noreply@company.ru.\n"
        )
        self.assertEqual(found, [], found)

    def test_keep_block_skips_secrets(self):
        found = self.scan_text("<!-- keep:start -->\nAKIAEXAMPLEEXAMPLE00\n<!-- keep:end -->\n")
        self.assertEqual(found, [])

    def test_frontmatter_zip_folder_suffix(self):
        with tempfile.TemporaryDirectory() as d:
            skill = Path(d) / "my-skill-main"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "---\nname: my-skill\ndescription: Does X. Use when asked for X.\n---\n\n# my-skill\n",
                encoding="utf-8")
            res = scan.run([str(skill / "SKILL.md")], Path(d), home=False)
        self.assertEqual(res["findings"], [])

    def test_unclosed_frontmatter(self):
        found = self.scan_text("---\nname: x\n\n# Body\n", name="SKILL.md")
        self.assertIn("E1", [f["id"] for f in found])


class Output(unittest.TestCase):
    def test_markdown_renders(self):
        md = scan.to_md(scan.run([], BAD, home=False))
        self.assertIn("🔴", md)
        self.assertIn("[C1]", md)
        self.assertIn("[F1]", md)
        for secret in ("AKIAEXAMPLEEXAMPLE00", "ghp_FAKEFAKE", "sk-ant-FAKE", "FAKE-hunter2",
                       "petrov.fake@company.ru"):
            self.assertNotIn(secret, md)  # ни в одной находке, не только в F1/F2

    def test_version(self):
        self.assertEqual(scan.VERSION, "1.1.0")


if __name__ == "__main__":
    unittest.main()
