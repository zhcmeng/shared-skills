#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_links.py 自己的测试。

    python tests/skill-judge/test_check_links.py

分两层：直接调函数验占位符规则与链接提取；再起子进程验退出码与输出格式。
坏链漏报比误报更糟——误报看得见，漏报看不见，所以「拿不准的写法」都按坏链测。
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = (HERE.parent.parent / "plugin" / "skills" / "skill-judge"
          / "scripts" / "check_links.py")
sys.path.insert(0, str(SCRIPT.parent))
import check_links  # noqa: E402


class PlaceholderRules(unittest.TestCase):
    def test_template_examples_are_placeholders(self):
        for target in (
            "../pages/概念-x.md",
            "../pages/页面名.md",
            "../research-reports-md/路径.md",
            "../pages/文档名称.md",
            "../pages/相对路径.md",
            "../pages/理解-X.md",
            "{主题}.md",
            "../pages/*.md",
        ):
            with self.subTest(target=target):
                self.assertTrue(check_links.is_placeholder(target))

    def test_real_names_are_not_placeholders(self):
        for target in (
            "../pages/概念-流量.md",
            "../../rules/引用规则.md",
            "../pages/signature.md",
            "../pages/概念-新.md",
            "../pages/概念-x2.md",
        ):
            with self.subTest(target=target):
                self.assertFalse(check_links.is_placeholder(target))

    def test_uncertain_names_are_left_to_the_human(self):
        # 图省事把 xxx 也当占位符，真实坏链就被吞掉了；规则故意不收它。
        self.assertFalse(check_links.is_placeholder("../pages/xxx.md"))


class LinkExtraction(unittest.TestCase):
    def links(self, text):
        return list(check_links.iter_links(text))

    def test_inline_link_and_image(self):
        self.assertEqual(
            self.links("[文字](x.md) ![说明](y.png)"),
            [(1, "x.md"), (1, "y.png")],
        )

    def test_title_and_angle_brackets(self):
        self.assertEqual(
            self.links('[甲](x.md "标题") [乙](<带 空格.md>)'),
            [(1, "x.md"), (1, "带 空格.md")],
        )

    def test_nested_parentheses(self):
        self.assertEqual(self.links("[甲](foo(1).md)"), [(1, "foo(1).md")])

    def test_linked_image_yields_both_targets(self):
        self.assertEqual(
            self.links("[![说明](img.png)](page.md)"),
            [(1, "img.png"), (1, "page.md")],
        )

    def test_malformed_destination_is_not_a_link(self):
        # 目标里有没转义的空格，CommonMark 也不把它当链接。
        self.assertEqual(self.links("[甲](a b.md)"), [])

    def test_fragment_stays_in_target(self):
        self.assertEqual(self.links("[甲](x.md#一节)"), [(1, "x.md#一节")])

    def test_fenced_code_is_ignored(self):
        text = "```python\n[甲](bad.md)\n```\n[乙](good.md)\n"
        self.assertEqual(self.links(text), [(4, "good.md")])

    def test_tilde_fence_is_ignored(self):
        text = "~~~\n[甲](bad.md)\n~~~\n[乙](good.md)\n"
        self.assertEqual(self.links(text), [(4, "good.md")])

    def test_unclosed_fence_runs_to_the_end(self):
        self.assertEqual(self.links("```\n[甲](bad.md)\n"), [])

    def test_inline_code_is_ignored(self):
        text = "写 `[甲](bad.md)` 与 ``[乙](also.md)`` 就行 [丙](good.md)"
        self.assertEqual(self.links(text), [(1, "good.md")])


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.skill = self.root / "demo-skill"
        (self.skill / "references").mkdir(parents=True)
        (self.skill / "references" / "exists.md").write_text(
            "# 存在\n", encoding="utf-8")

    def write(self, relative, text):
        path = self.skill / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(SCRIPT), *args],
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_all_targets_exist_exits_zero(self):
        self.write("SKILL.md", "\n".join([
            "# 技能",
            "",
            "[参考](references/exists.md)",
            "![图](references/exists.md)",
            "[节](references/exists.md#一节)",
            "[外链](https://example.com/x.md)",
            "[邮件](mailto:a@example.com)",
            "[根](/absolute/path.md)",
            "[盘](C:/absolute/path.md)",
            "`[行内示例](references/missing.md)`",
            "",
            "```",
            "[围栏示例](references/missing.md)",
            "```",
            "",
            "[占位](../pages/页面名.md)",
        ]))
        result = self.run_script(str(self.skill))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("没有坏链", result.stdout)
        self.assertIn("占位符（跳过）", result.stdout)
        self.assertNotIn("missing.md", result.stdout)

    def test_missing_target_reports_file_line_and_exits_one(self):
        self.write("SKILL.md", "\n".join([
            "# 技能",
            "",
            "[丢了](references/missing.md)",
            "![也丢了](img/missing.png)",
        ]))
        result = self.run_script(str(self.skill))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("SKILL.md:3: references/missing.md", result.stdout)
        self.assertIn("SKILL.md:4: img/missing.png", result.stdout)

    def test_placeholders_are_listed_but_not_bad(self):
        self.write("SKILL.md", "\n".join([
            "[一](../pages/概念-x.md)",
            "[二](../pages/页面名.md)",
            "[三](../research-reports-md/路径.md)",
            "[四](../pages/文档名称.md)",
        ]))
        result = self.run_script(str(self.skill))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("4 条占位符（跳过）", result.stdout)
        for target in ("概念-x.md", "页面名.md", "路径.md", "文档名称.md"):
            self.assertIn(target, result.stdout)

    def test_uncertain_missing_target_is_a_bad_link(self):
        self.write("SKILL.md", "[五](../pages/xxx.md)\n")
        result = self.run_script(str(self.skill))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("SKILL.md:1: ../pages/xxx.md", result.stdout)

    def test_fragment_angle_brackets_and_percent_encoding(self):
        (self.skill / "references" / "带 空格.md").write_text(
            "# 带空格\n", encoding="utf-8")
        self.write("SKILL.md", "\n".join([
            "[节](references/exists.md#标题)",
            "[空格](<references/带 空格.md>)",
            "[编码](references/%E5%B8%A6%20%E7%A9%BA%E6%A0%BC.md)",
        ]))
        result = self.run_script(str(self.skill))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("没有坏链", result.stdout)

    def test_nested_markdown_is_scanned(self):
        self.write("references/nested.md", "[丢](../missing.md)\n")
        result = self.run_script(str(self.skill))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("nested.md:1: ../missing.md", result.stdout)

    def test_single_file_input(self):
        path = self.write("one.md", "[丢](missing.md)\n")
        result = self.run_script(str(path))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("one.md:1: missing.md", result.stdout)

    def test_help_prints_the_rules(self):
        result = self.run_script("--help")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("占位符", result.stdout)
        self.assertIn("概念-x.md", result.stdout)

    def test_missing_input_path_exits_two(self):
        result = self.run_script(str(self.root / "nope"))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_directory_without_markdown_exits_two(self):
        empty = self.root / "empty"
        empty.mkdir()
        result = self.run_script(str(empty))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_non_markdown_file_exits_two(self):
        path = self.skill / "notes.txt"
        path.write_text("不是 Markdown\n", encoding="utf-8")
        result = self.run_script(str(path))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_undecodable_file_exits_two(self):
        path = self.skill / "bad.md"
        path.write_bytes(b"\xff\xfe\x00bad")
        result = self.run_script(str(path))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("读不了", result.stderr)


if __name__ == "__main__":
    unittest.main()
