import os
import sys
import unittest

# 把 scripts/ 插进 sys.path，照 download-md-images 那份测试的写法
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from markdown import PlaceholderLeftover, convert_tables


class TestConvertTables(unittest.TestCase):
    def test_simple_table_becomes_pipe_table(self):
        html = ("<table><tr><th>A</th><th>B</th></tr>"
                "<tr><td>1</td><td>2</td></tr></table>")
        out = convert_tables(html)
        self.assertIn("| A", out)
        self.assertIn("| 1", out)
        self.assertNotIn("<table", out)
        self.assertNotIn("<td", out)

    def test_merged_cell_keeps_text_and_row_widths_match(self):
        html = ('<table><tr><th colspan="2">合计</th></tr>'
                '<tr><td>左</td><td>右</td></tr></table>')
        out = convert_tables(html)
        self.assertIn("合计", out)
        self.assertIn("左", out)
        self.assertIn("右", out)
        self.assertNotIn("<table", out)
        widths = {line.count("|") for line in out.splitlines() if line.strip()}
        self.assertEqual(len(widths), 1)

    def test_cell_with_inner_tags_keeps_only_text(self):
        html = "<table><tr><td><span>粗</span><b>体</b></td></tr></table>"
        out = convert_tables(html)
        self.assertIn("粗体", out)
        self.assertNotIn("<span", out)
        self.assertNotIn("<b>", out)

    def test_pipe_in_cell_is_escaped(self):
        html = "<table><tr><td>a|b</td></tr></table>"
        out = convert_tables(html)
        self.assertIn("a\\|b", out)

    def test_html_outside_table_is_left_alone(self):
        html = "<p>前面</p><table><tr><td>x</td></tr></table><div>后面</div>"
        out = convert_tables(html)
        self.assertIn("<p>前面</p>", out)
        self.assertIn("<div>后面</div>", out)

    def test_nested_table_is_one_span(self):
        html = ("<table><tr><td>外"
                "<table><tr><td>内</td></tr></table>"
                "</td></tr></table>")
        out = convert_tables(html)
        self.assertIn("外", out)
        self.assertIn("内", out)
        self.assertNotIn("<table", out)

    def test_text_without_table_is_unchanged(self):
        text = "# 标题\n\n正文，里面有个 < 号。\n"
        self.assertEqual(convert_tables(text), text)

    def test_leftover_placeholder_raises(self):
        with self.assertRaises(PlaceholderLeftover):
            convert_tables("正文里混进了 \x00T0\x00 这种记号")


if __name__ == "__main__":
    unittest.main()
