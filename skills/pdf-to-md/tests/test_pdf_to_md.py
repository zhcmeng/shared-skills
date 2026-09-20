import argparse
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from concurrent.futures import Future
from unittest import mock

import requests

# 把 scripts/ 插进 sys.path，照 download-md-images 那份测试的写法
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import aistudio
import convert
from aistudio import JobFailed, NetworkError, SubmitRejected

import markdown
from markdown import (JsonlLineError, Page, PlaceholderLeftover, allocate_names,
                      assemble, clean_markdown, convert_tables, image_downloads,
                      normalize_blank_lines, parse_jsonl, rewrite_image_refs,
                      strip_page_markers, strip_wrapper_tags)


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

    def test_unclosed_table_does_not_swallow_later_tables(self):
        # 正文里冒出一个孤立的 <table（PDF 讲 HTML 时很常见）时，
        # 它自己原样留着，但后面那张格式正常的表格照样要转
        html = ("<p>讲个 <table 标签</p>"
                "<table><tr><th>A</th><th>B</th></tr>"
                "<tr><td>1</td><td>2</td></tr></table>")
        out = convert_tables(html)
        self.assertIn("| A", out)
        self.assertIn("| 1", out)
        self.assertNotIn("<tr>", out)
        self.assertNotIn("<td>", out)

    def test_text_without_table_is_unchanged(self):
        text = "# 标题\n\n正文，里面有个 < 号。\n"
        self.assertEqual(convert_tables(text), text)

    def test_leftover_placeholder_raises(self):
        with self.assertRaises(PlaceholderLeftover):
            convert_tables("正文里混进了 \x00T0\x00 这种记号")


class TestStripWrapperTags(unittest.TestCase):
    def test_wrapper_tags_are_removed_but_text_stays(self):
        html = '<div style="text-align: center;">中间的话</div>'
        self.assertEqual(strip_wrapper_tags(html), "中间的话")

    def test_all_wrapper_names(self):
        for name in ("div", "span", "center", "html", "body", "p"):
            out = strip_wrapper_tags(f"<{name}>x</{name}>")
            self.assertEqual(out, "x", name)

    def test_attribute_less_unknown_tag_is_dropped(self):
        self.assertEqual(strip_wrapper_tags("前<image>后"), "前后")

    def test_stray_tag_is_only_dropped_whole(self):
        # 残标签只认光秃秃的开标签；带属性的 <image …> 连同收尾那半一起留着，
        # 不能只删收尾的一半、留下个配不平的标签
        html = '<image src="a.png">图</image>'
        self.assertEqual(strip_wrapper_tags(html), html)

    def test_bare_stray_pair_is_dropped_whole(self):
        # 开标签和收尾标签都是光秃秃的，是一对，整对删干净
        self.assertEqual(strip_wrapper_tags("<image>图</image>"), "图")

    def test_lone_stray_closing_tag_is_kept(self):
        # 没有配对的裸开标签，说明它那个开标签带了属性、被上面那条留下了，
        # 这个收尾标签也得留着，不然又剩半个
        self.assertEqual(strip_wrapper_tags("图</image>"), "图</image>")

    def test_text_that_merely_looks_like_a_tag_is_left_alone(self):
        # 认不出来又没属性的，不能一律当残标签删——正文里这些形状很常见，
        # 删了是静默丢内容，比留着一个看得见的标签坏得多
        for text in ("<name>", "List<String>", "x<y>z", "<request> 的内容"):
            self.assertEqual(strip_wrapper_tags(text), text, text)

    def test_table_and_inline_tags_are_kept(self):
        for html in ("<table><tr><td>x</td></tr></table>",
                     "<b>粗</b>", "<img src=\"a.jpg\" width=\"73%\">"):
            self.assertEqual(strip_wrapper_tags(html), html)

    def test_unknown_tag_with_attribute_is_left_alone(self):
        html = '<custom data-x="1">x</custom>'
        self.assertEqual(strip_wrapper_tags(html), html)


class TestStripPageMarkers(unittest.TestCase):
    def test_bare_page_number_line_is_dropped(self):
        self.assertEqual(strip_page_markers("第 3 页"), "")

    def test_page_number_with_total_is_dropped(self):
        for line in ("第 3 页 / 共 10 页", "第 3 页（共 10 页）", "第3页，共10页"):
            self.assertEqual(strip_page_markers(line), "", line)

    def test_dashed_page_number_is_dropped(self):
        self.assertEqual(strip_page_markers("- 12 -"), "")

    def test_english_page_marker_is_dropped(self):
        for line in ("Page 3", "Page 3 of 10", "page 12"):
            self.assertEqual(strip_page_markers(line), "", line)

    def test_marker_left_in_the_middle_of_a_line_is_kept(self):
        # 分不出来那是页码还是正文，宁可不删
        self.assertEqual(strip_page_markers("详见第 3 页"), "详见第 3 页")

    def test_only_the_marker_line_goes(self):
        self.assertEqual(strip_page_markers("正文\n第 3 页\n后文"), "正文\n\n后文")

    def test_a_line_that_merely_starts_with_the_word_page_is_kept(self):
        self.assertEqual(strip_page_markers("Page 3 讲了协议语义"),
                         "Page 3 讲了协议语义")

    def test_normal_text_is_untouched(self):
        text = "# 标题\n\n正文\n\n- 列表项"
        self.assertEqual(strip_page_markers(text), text)


class TestNormalizeBlankLines(unittest.TestCase):
    def test_trailing_spaces_gone(self):
        self.assertEqual(normalize_blank_lines("a   \nb\t\n"), "a\nb")

    def test_three_or_more_newlines_become_two(self):
        self.assertEqual(normalize_blank_lines("a\n\n\n\n\nb"), "a\n\nb")

    def test_two_newlines_are_kept(self):
        self.assertEqual(normalize_blank_lines("a\n\nb"), "a\n\nb")

    def test_leading_and_trailing_blank_lines_stripped(self):
        self.assertEqual(normalize_blank_lines("\n\n  a  \n\n"), "a")


class TestStripWrapperTagsStrayPairing(unittest.TestCase):
    """残标签按位置配对，不按名字。

    一份正文里可能既有光秃秃的 <image>，又有带属性的 <image …></image>；
    按名字收一个「出现过裸开标签」的集合，就会把后者那个 </image> 也删掉，
    剩半个配不平的开标签。
    """

    def test_bare_pair_before_attributed_pair(self):
        text = '<image>a</image> 中 <image src="b.png">c</image>'
        self.assertEqual(strip_wrapper_tags(text),
                         'a 中 <image src="b.png">c</image>')

    def test_attributed_pair_before_bare_pair(self):
        text = '<image src="b.png">c</image> 中 <image>a</image>'
        self.assertEqual(strip_wrapper_tags(text),
                         '<image src="b.png">c</image> 中 a')

    def test_bare_open_without_a_close_is_dropped(self):
        # 实测到的残留形状：光秃秃的开标签，后面压根没有收尾标签
        self.assertEqual(strip_wrapper_tags("<image>没闭合"), "没闭合")

    def test_each_bare_pair_is_dropped_on_its_own(self):
        self.assertEqual(strip_wrapper_tags("<image>a</image><image>b</image>"),
                         "ab")


class TestRewriteImageRefs(unittest.TestCase):
    def setUp(self):
        self.names = {"imgs/img_in_image_box_1_2_3_4.jpg": "img_in_image_box_1_2_3_4.jpg"}

    def resolve(self, src):
        return self.names.get(src)

    def test_img_tag_becomes_markdown(self):
        html = '<img src="imgs/img_in_image_box_1_2_3_4.jpg" alt="Image" width="73%" />'
        out = rewrite_image_refs(html, self.resolve)
        self.assertEqual(out, "![](images/img_in_image_box_1_2_3_4.jpg)")

    def test_markdown_image_is_rewritten_too(self):
        out = rewrite_image_refs("![alt](imgs/img_in_image_box_1_2_3_4.jpg)", self.resolve)
        self.assertEqual(out, "![](images/img_in_image_box_1_2_3_4.jpg)")

    def test_markdown_image_with_title_is_rewritten(self):
        out = rewrite_image_refs('![a](imgs/img_in_image_box_1_2_3_4.jpg "标题")',
                                 self.resolve)
        self.assertEqual(out, "![](images/img_in_image_box_1_2_3_4.jpg)")

    def test_unknown_src_is_left_alone(self):
        html = '<img src="https://example.com/x.png">'
        self.assertEqual(rewrite_image_refs(html, self.resolve), html)

    def test_already_localized_ref_is_left_alone(self):
        md = "![](images/img_in_image_box_1_2_3_4.jpg)"
        self.assertEqual(rewrite_image_refs(md, self.resolve), md)

    def test_no_resolve_callable_still_works(self):
        self.assertEqual(rewrite_image_refs("正文", None), "正文")


def jsonl_line(pages, error_code=0, error_msg="Success", num_pages=None):
    """造一行 JSONL。pages 是 [(正文, {图片名: 网址}), …]。

    num_pages 默认跟着项数走（跟实测结果一样）；显式给一个别的数，
    是为了造出「numPages 跟项数对不上」的行——那正是实现容易信错的坑。
    """
    return json.dumps({
        "errorCode": error_code,
        "errorMsg": error_msg,
        "logId": "x",
        "result": {
            "dataInfo": {"numPages": len(pages) if num_pages is None else num_pages},
            "layoutParsingResults": [
                {"markdown": {"text": text, "images": images}}
                for text, images in pages
            ],
        },
    }, ensure_ascii=False)


class TestParseJsonl(unittest.TestCase):
    def test_flat_order_is_line_then_page(self):
        raw = "\n".join([
            jsonl_line([("一", {}), ("二", {})]),
            jsonl_line([("三", {})]),
        ])
        pages = parse_jsonl(raw)
        self.assertEqual([p.text for p in pages], ["一", "二", "三"])
        self.assertEqual([p.index for p in pages], [0, 1, 2])

    def test_page_count_is_not_hardcoded_to_three(self):
        raw = "\n".join([jsonl_line([("一", {})]), jsonl_line([("二", {}), ("三", {})])])
        self.assertEqual(len(parse_jsonl(raw)), 3)

    def test_blank_lines_are_skipped(self):
        raw = jsonl_line([("一", {})]) + "\n\n   \n"
        self.assertEqual(len(parse_jsonl(raw)), 1)

    def test_images_are_collected_per_page(self):
        raw = jsonl_line([("一", {"imgs/a.jpg": "https://x/a.jpg"}),
                          ("二", {"imgs/a.jpg": "https://x/b.jpg"})])
        pages = parse_jsonl(raw)
        self.assertEqual(pages[0].images, {"imgs/a.jpg": "https://x/a.jpg"})
        self.assertEqual(pages[1].images, {"imgs/a.jpg": "https://x/b.jpg"})

    def test_missing_markdown_field_becomes_empty_text(self):
        raw = json.dumps({"errorCode": 0, "result": {"layoutParsingResults": [{}]}})
        pages = parse_jsonl(raw)
        self.assertEqual(pages[0].text, "")
        self.assertEqual(pages[0].images, {})

    def test_empty_result_gives_no_pages(self):
        raw = json.dumps({"errorCode": 0, "result": {}})
        self.assertEqual(parse_jsonl(raw), [])

    def test_line_level_error_raises(self):
        raw = jsonl_line([("一", {})], error_code=10004, error_msg="文件格式不支持")
        with self.assertRaises(JsonlLineError) as ctx:
            parse_jsonl(raw)
        self.assertIn("文件格式不支持", str(ctx.exception))
        self.assertIn("第 1 行", str(ctx.exception))

    def test_page_count_follows_the_items_not_num_pages(self):
        # numPages 是行内标记，靠不住；页数只跟 layoutParsingResults 的项数走
        raw = jsonl_line([("一", {}), ("二", {})], num_pages=9)
        self.assertEqual(len(parse_jsonl(raw)), 2)

    def test_a_smaller_num_pages_does_not_truncate_the_pages(self):
        # 反方向：numPages 比项数小的时候也不许拿它截断
        raw = jsonl_line([("一", {}), ("二", {})], num_pages=1)
        self.assertEqual([p.text for p in parse_jsonl(raw)], ["一", "二"])

    def test_unparsable_line_raises_with_line_number(self):
        # 代理塞回来的 HTML、被截断的半行、任何非 JSON：解析不了也得抛自己的
        # 异常类。上层并发那层只接得住 JsonlLineError，漏出去会让整批跑崩，
        # 而不是只让这一份失败。
        raw = jsonl_line([("一", {})]) + '\n{"errorCode": 0, "result": {"layout'
        with self.assertRaises(JsonlLineError) as ctx:
            parse_jsonl(raw)
        self.assertIn("第 2 行", str(ctx.exception))

    def test_non_object_top_level_raises(self):
        # 合法 JSON、形状不对：网关回 null／[]／裸数字／裸字符串。
        # 这些一样会让 obj.get(...) 抛 AttributeError 漏出去、掀翻整批。
        for raw in ("null", "[]", "123", '"成功"'):
            with self.assertRaises(JsonlLineError) as ctx:
                parse_jsonl(raw)
            self.assertIn("第 1 行", str(ctx.exception), raw)

    def test_result_that_is_not_an_object_raises(self):
        raw = json.dumps({"errorCode": 0, "result": "x"})
        with self.assertRaises(JsonlLineError) as ctx:
            parse_jsonl(raw)
        self.assertIn("result", str(ctx.exception))
        self.assertIn("第 1 行", str(ctx.exception))

    def test_malformed_nested_fields_raise(self):
        cases = [
            {"result": {"layoutParsingResults": "x"}},
            {"result": {"layoutParsingResults": [42]}},
            {"result": {"layoutParsingResults": [{"markdown": "x"}]}},
            {"result": {"layoutParsingResults": [{"markdown": {"images": "x"}}]}},
            {"result": {"layoutParsingResults": [{"markdown": {"text": 42}}]}},
        ]
        for case in cases:
            raw = json.dumps({"errorCode": 0, **case})
            with self.assertRaises(JsonlLineError) as ctx:
                parse_jsonl(raw)
            self.assertIn("第 1 行", str(ctx.exception), case)

    def test_malformed_shape_on_a_later_line_reports_that_line(self):
        raw = jsonl_line([("一", {})]) + "\n" + json.dumps(
            {"errorCode": 0, "result": 5})
        with self.assertRaises(JsonlLineError) as ctx:
            parse_jsonl(raw)
        self.assertIn("第 2 行", str(ctx.exception))


class TestAllocateNames(unittest.TestCase):
    def make(self, pages):
        return [Page(index=i, text="", images=imgs) for i, imgs in enumerate(pages)]

    def test_normal_case_keeps_the_api_name(self):
        pages = self.make([{"imgs/img_in_image_box_1_2_3_4.jpg": "https://x/a"}])
        names = allocate_names(pages)
        self.assertEqual(names[(0, "imgs/img_in_image_box_1_2_3_4.jpg")],
                         "img_in_image_box_1_2_3_4.jpg")

    def test_same_position_on_two_pages_gets_two_files(self):
        # 实测撞过：第 0 页复制一份插到最前，两页的键一字不差
        pages = self.make([
            {"imgs/img_in_image_box_152_136_1048_296.jpg": "https://x/markdown_0/a.jpg"},
            {"imgs/img_in_image_box_152_136_1048_296.jpg": "https://x/markdown_1/a.jpg"},
        ])
        names = allocate_names(pages)
        first = names[(0, "imgs/img_in_image_box_152_136_1048_296.jpg")]
        second = names[(1, "imgs/img_in_image_box_152_136_1048_296.jpg")]
        self.assertEqual(first, "img_in_image_box_152_136_1048_296.jpg")
        self.assertEqual(second, "img_in_image_box_152_136_1048_296-2.jpg")

    def test_third_collision_gets_dash_three(self):
        pages = self.make([
            {"imgs/a.jpg": "https://x/1/a.jpg"},
            {"imgs/a.jpg": "https://x/2/a.jpg"},
            {"imgs/a.jpg": "https://x/3/a.jpg"},
        ])
        names = allocate_names(pages)
        self.assertEqual(names[(2, "imgs/a.jpg")], "a-3.jpg")

    def test_same_url_twice_is_one_file(self):
        pages = self.make([
            {"imgs/a.jpg": "https://x/same"},
            {"imgs/b.jpg": "https://x/same"},
        ])
        names = allocate_names(pages)
        self.assertEqual(names[(0, "imgs/a.jpg")], names[(1, "imgs/b.jpg")])

    def test_two_documents_do_not_share_the_name_table(self):
        one = allocate_names(self.make([{"imgs/a.jpg": "https://x/1"}]))
        two = allocate_names(self.make([{"imgs/a.jpg": "https://x/2"}]))
        self.assertEqual(one[(0, "imgs/a.jpg")], "a.jpg")
        self.assertEqual(two[(0, "imgs/a.jpg")], "a.jpg")

    def test_name_without_extension_still_gets_a_suffix(self):
        pages = self.make([{"imgs/a": "https://x/1"}, {"imgs/a": "https://x/2"}])
        names = allocate_names(pages)
        self.assertEqual(names[(1, "imgs/a")], "a-2")


class TestImageDownloads(unittest.TestCase):
    def test_dedupes_by_url_keeping_order(self):
        pages = [Page(index=0, text="", images={"imgs/a.jpg": "https://x/1",
                                                "imgs/b.jpg": "https://x/2"}),
                 Page(index=1, text="", images={"imgs/c.jpg": "https://x/1"})]
        names = allocate_names(pages)
        self.assertEqual(image_downloads(pages, names),
                         [("a.jpg", "https://x/1"), ("b.jpg", "https://x/2")])

    def test_local_names_come_from_the_name_table_not_the_basename(self):
        # 撞名的两份：查表给出 a.jpg 与 a-2.jpg，而两者的 basename 都是 a.jpg。
        # 不查表、直接取 basename 的写法会在这里露馅。
        pages = [Page(index=0, text="", images={"imgs/a.jpg": "https://x/1"}),
                 Page(index=1, text="", images={"imgs/a.jpg": "https://x/2"})]
        names = allocate_names(pages)
        self.assertEqual(image_downloads(pages, names),
                         [("a.jpg", "https://x/1"), ("a-2.jpg", "https://x/2")])

    def test_same_url_twice_on_one_page_is_one_download(self):
        pages = [Page(index=0, text="", images={"imgs/a.jpg": "https://x/same",
                                                "imgs/b.jpg": "https://x/same"})]
        names = allocate_names(pages)
        self.assertEqual(image_downloads(pages, names),
                         [("a.jpg", "https://x/same")])

    def test_order_is_appearance_order_not_sorted(self):
        # 后出现的那张，网址按字典序反而更靠前——排序实现会露馅
        pages = [Page(index=0, text="", images={"imgs/b.jpg": "https://x/z"}),
                 Page(index=1, text="", images={"imgs/a.jpg": "https://x/a"})]
        names = allocate_names(pages)
        self.assertEqual([url for _, url in image_downloads(pages, names)],
                         ["https://x/z", "https://x/a"])


class TestCleanMarkdown(unittest.TestCase):
    def test_full_pipeline_on_a_sample_page(self):
        raw = ('<div style="text-align: center;">'
               '<img src="imgs/img_in_image_box_1_2_3_4.jpg" alt="Image" width="73%" />'
               '</div>\n\n\n\n正文   \n')
        names = {"imgs/img_in_image_box_1_2_3_4.jpg": "img_in_image_box_1_2_3_4.jpg"}
        out = clean_markdown(raw, names.get)
        self.assertEqual(out, "![](images/img_in_image_box_1_2_3_4.jpg)\n\n正文")

    def test_table_becomes_markdown_then_whitespace_is_normalized(self):
        raw = "<table><tr><th>A</th></tr><tr><td>1</td></tr></table>\n\n\n\n尾"
        out = clean_markdown(raw, None)
        self.assertNotIn("<table", out)
        self.assertIn("| A", out)
        self.assertNotIn("\n\n\n", out)

    def test_page_number_div_is_unwrapped_then_dropped(self):
        # 先拆掉包裹标签，那一行就剩一个光页码，再按页码行删掉
        raw = '<div class="page-number">第 3 页</div>\n正文'
        self.assertEqual(clean_markdown(raw, None), "正文")

    def test_leftover_placeholder_raises(self):
        # 记号从流水线中途注入，这样末检才是唯一能抓住它的地方。
        # 直接喂一个带记号的输入不行——convert_tables 的入口守卫会先拦下，
        # 那样测的是它、不是末检（删掉末检全套仍然全绿）。
        with mock.patch("markdown.strip_page_markers",
                        side_effect=lambda t: t + markdown._PLACEHOLDER.format(7)):
            with self.assertRaises(PlaceholderLeftover):
                clean_markdown("正文", None)


class TestAssemble(unittest.TestCase):
    def test_pages_are_joined_in_order(self):
        pages = [Page(index=0, text="一", images={}),
                 Page(index=1, text="二", images={})]
        self.assertEqual(assemble(pages, {}), "一\n\n二")

    def test_images_are_rewritten_per_page_not_globally(self):
        pages = [
            Page(index=0, text='<img src="imgs/a.jpg">',
                 images={"imgs/a.jpg": "https://x/1"}),
            Page(index=1, text='<img src="imgs/a.jpg">',
                 images={"imgs/a.jpg": "https://x/2"}),
        ]
        names = allocate_names(pages)
        out = assemble(pages, names)
        self.assertEqual(out, "![](images/a.jpg)\n\n![](images/a-2.jpg)")

    def test_bare_filename_ref_resolves_through_the_name_table(self):
        # 正文里用的是裸文件名（不带 imgs/ 前缀），名字表里的 src 带目录。
        # 折 lookup 时若只登记带目录的那一种键，这条就改不动。
        pages = [Page(index=0, text='<img src="img_in_image_box_1_2_3_4.jpg">',
                      images={"imgs/img_in_image_box_1_2_3_4.jpg": "https://x/1"})]
        names = allocate_names(pages)
        self.assertEqual(assemble(pages, names),
                         "![](images/img_in_image_box_1_2_3_4.jpg)")

    def test_empty_page_list_gives_empty_string(self):
        self.assertEqual(assemble([], {}), "")


class FakeResponse:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body
        self.text = text

    def json(self):
        if self._body is None:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._body


class BrokenBodyResponse:
    """压缩体坏掉的样子：读 JSON 与读正文都抛 ContentDecodingError。

    它不是 ValueError 的子类，所以 _body_of 与 _rejected_from 那两层
    except 少写一条，它就会原样穿出 submit——Task 12 的捕获表接不住。
    """

    status_code = 200

    def json(self):
        raise requests.exceptions.ContentDecodingError("解不开压缩体")

    @property
    def text(self):
        raise requests.exceptions.ContentDecodingError("解不开压缩体")


class TestGetToken(unittest.TestCase):
    def test_the_env_var_name_is_the_one_the_settings_file_uses(self):
        # 这个名字是跟用户 ~/.claude/settings.json 的约定。改了它不会报错，
        # 只会悄悄读不到用户已经配好的 token——那是最难查的一种坏法。
        self.assertEqual(aistudio.TOKEN_ENV, "PADDLEOCR_MCP_AISTUDIO_ACCESS_TOKEN")

    def test_reads_the_env_var(self):
        with mock.patch.dict(os.environ, {aistudio.TOKEN_ENV: "abc"}, clear=False):
            self.assertEqual(aistudio.get_token(), "abc")

    def test_missing_token_says_where_to_put_it(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit) as ctx:
                aistudio.get_token()
        self.assertIn(aistudio.TOKEN_ENV, str(ctx.exception))
        self.assertIn("settings.json", str(ctx.exception))


class TestSubmit(unittest.TestCase):
    def test_url_goes_in_a_json_body(self):
        captured = {}

        def fake_post(url, **kw):
            captured.update(kw, url=url)
            return FakeResponse(body={"code": 0, "data": {"jobId": "j1"}})

        with mock.patch.object(requests, "post", fake_post):
            job_id = aistudio.submit("https://example.com/a.pdf", "PaddleOCR-VL-1.6", "t")
        self.assertEqual(job_id, "j1")
        self.assertEqual(captured["url"], aistudio.JOB_URL)
        self.assertEqual(captured["json"]["fileUrl"], "https://example.com/a.pdf")
        self.assertEqual(captured["json"]["model"], "PaddleOCR-VL-1.6")
        self.assertEqual(captured["json"]["optionalPayload"],
                         {"useDocOrientationClassify": False,
                          "useDocUnwarping": False,
                          "useChartRecognition": False})

    def test_local_file_goes_as_multipart(self):
        captured = {}

        def fake_post(url, **kw):
            captured.update(kw, url=url)
            return FakeResponse(body={"code": 0, "data": {"jobId": "j2"}})

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = os.path.join(tmp.name, "fixture.pdf")
        with open(path, "wb") as f:
            f.write(b"%PDF-1.4\n")
        with mock.patch.object(requests, "post", fake_post):
            aistudio.submit(path, "PP-StructureV3", "t")
        self.assertNotIn("json", captured)
        self.assertEqual(captured["url"], aistudio.JOB_URL)
        self.assertEqual(captured["data"]["model"], "PP-StructureV3")
        self.assertIn("file", captured["files"])

    def test_missing_local_file_raises_oserror_not_submit_rejected(self):
        # 文件不存在是本机的问题，不是「服务拒了这次提交」，也不该白白重试。
        # 这个形状 Task 12 的捕获表依赖着：它接了 OSError，漏出去就是整批崩。
        def refuse(*a, **k):
            self.fail("这条用例不该发请求")

        with mock.patch.object(requests, "post", refuse):
            with self.assertRaises(OSError):
                aistudio.submit("/no/such/file.pdf", "m", "t")

    def test_endpoint_and_model_are_the_ones_the_service_documents(self):
        # 规格逐字规定了这两处，别顺手统一模型名写法、也别改域名
        self.assertEqual(aistudio.JOB_URL,
                         "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs")
        self.assertEqual(aistudio.DEFAULT_MODEL, "PaddleOCR-VL-1.6")

    def test_http_400_becomes_submit_rejected_with_the_service_wording(self):
        resp = FakeResponse(status_code=400,
                            body={"traceId": "t1", "code": 10004,
                                  "msg": "文件格式不支持"})
        with mock.patch.object(requests, "post", lambda *a, **k: resp):
            with self.assertRaises(SubmitRejected) as ctx:
                aistudio.submit("https://example.com/a.pdf", "m", "t")
        self.assertEqual(ctx.exception.code, 10004)
        self.assertIn("文件格式不支持", str(ctx.exception))

    def test_non_json_error_body_does_not_crash(self):
        # 网关返回 HTML 错误页时，报出来的该是「服务说了什么」而不是 JSON 解码错
        resp = FakeResponse(status_code=502, text="<html>Bad Gateway</html>")
        with mock.patch.object(requests, "post", lambda *a, **k: resp):
            with self.assertRaises(SubmitRejected) as ctx:
                aistudio.submit("https://example.com/a.pdf", "m", "t")
        self.assertIn("Bad Gateway", str(ctx.exception))

    def test_a_broken_response_body_is_a_rejection_not_a_crash(self):
        with mock.patch.object(requests, "post",
                               lambda *a, **k: BrokenBodyResponse()):
            with self.assertRaises(SubmitRejected) as ctx:
                aistudio.submit("https://example.com/a.pdf", "m", "t")
        self.assertIn("HTTP 200", str(ctx.exception))

    def test_code_nonzero_in_a_200_body_is_also_a_rejection(self):
        # 带上 data/jobId：不带的话「没任务号」那一支先把它拒了，
        # 这条用例就再也抓不到「非 0 的 code 也算拒」这个判断
        resp = FakeResponse(status_code=200,
                            body={"code": 10002, "msg": "文件 URL 无法识别",
                                  "data": {"jobId": "j0"}})
        with mock.patch.object(requests, "post", lambda *a, **k: resp):
            with self.assertRaises(SubmitRejected) as ctx:
                aistudio.submit("https://example.com/a.pdf", "m", "t")
        self.assertIn("文件 URL 无法识别", str(ctx.exception))

    def test_200_with_a_non_json_body_is_a_rejection(self):
        # 网关回了 200 却不是 JSON：不能崩在解码上，也不能让 ValueError 漏出去
        resp = FakeResponse(status_code=200, text="<html>hello</html>")
        with mock.patch.object(requests, "post", lambda *a, **k: resp):
            with self.assertRaises(SubmitRejected) as ctx:
                aistudio.submit("https://example.com/a.pdf", "m", "t")
        self.assertIn("hello", str(ctx.exception))

    def test_200_without_a_job_id_is_a_rejection(self):
        # 说成功却没给任务号——拿不到 jobId 就走不下去，得算提交被拒
        resp = FakeResponse(status_code=200, body={"code": 0, "msg": "Success"})
        with mock.patch.object(requests, "post", lambda *a, **k: resp):
            with self.assertRaises(SubmitRejected) as ctx:
                aistudio.submit("https://example.com/a.pdf", "m", "t")
        self.assertIn("Success", str(ctx.exception))

    def test_network_error_is_retried_then_reported_as_such(self):
        calls = []
        naps = []

        def boom(*a, **k):
            calls.append(1)
            raise requests.ConnectionError("getaddrinfo failed")

        # 盯 sleep，不把 RETRY_DELAY patch 成 0：后者只在 _retry 写成函数体
        # 回落时才起作用，失效时唯一的症状是整套慢几秒，没有断言能发现。
        with mock.patch.object(requests, "post", boom), \
             mock.patch.object(aistudio.time, "sleep", naps.append):
            with self.assertRaises(NetworkError) as ctx:
                aistudio.submit("https://example.com/a.pdf", "m", "t")
        self.assertEqual(len(calls), aistudio.RETRY_ATTEMPTS)
        # 每次失败后睡一觉；最后一次失败直接抛，不再睡
        self.assertEqual(len(naps), aistudio.RETRY_ATTEMPTS - 1)
        self.assertIn("连不上", str(ctx.exception))


class TestPoll(unittest.TestCase):
    def run_poll(self, states, on_progress=None):
        seq = list(states)
        # 把「问一次」和「等一次」按发生顺序记进一条流水。只记睡了几次不够：
        # 「两次询问之间等」和「问完两次、返回前再睡一下」都是睡一次。
        # 也不把 POLL_INTERVAL patch 成 0——那样只在 poll 直接读常量时起作用，
        # 失效时唯一的症状是每条用例真睡几秒，没有断言能发现。
        self.trace = []

        def fake_get(url, **kw):
            self.trace.append("get")
            return FakeResponse(body={"code": 0, "data": seq.pop(0)})

        def note_sleep(seconds):
            self.trace.append(("sleep", seconds))

        with mock.patch.object(requests, "get", fake_get), \
             mock.patch.object(aistudio.time, "sleep", note_sleep):
            return aistudio.poll("j1", "t", on_progress=on_progress)

    def test_asks_the_job_url_with_the_token(self):
        seen = {}

        def fake_get(url, **kw):
            seen["url"] = url
            seen.update(kw)
            return FakeResponse(body={"code": 0, "data": {
                "jobId": "j1", "state": "done",
                "resultUrl": {"jsonUrl": "u"}}})

        with mock.patch.object(requests, "get", fake_get):
            aistudio.poll("j1", "tok")
        self.assertEqual(seen["url"], aistudio.JOB_URL + "/j1")
        self.assertEqual(seen["headers"]["Authorization"], "bearer tok")
        self.assertEqual(seen["timeout"], aistudio.SMALL_TIMEOUT)

    def test_pending_then_done_returns_the_jsonl_url(self):
        url = self.run_poll([
            {"jobId": "j1", "state": "pending"},
            {"jobId": "j1", "state": "done",
             "extractProgress": {"extractedPages": 3, "totalPages": 3},
             "resultUrl": {"jsonUrl": "https://x/r.jsonl"}},
        ])
        self.assertEqual(url, "https://x/r.jsonl")
        # 问 → 等一个 POLL_INTERVAL → 再问；拿到结果就走，不在 done 之后再睡
        self.assertEqual(self.trace,
                         ["get", ("sleep", aistudio.POLL_INTERVAL), "get"])

    def test_running_reports_progress(self):
        seen = []
        self.run_poll([
            {"jobId": "j1", "state": "running",
             "extractProgress": {"extractedPages": 6, "totalPages": 105}},
            {"jobId": "j1", "state": "done", "resultUrl": {"jsonUrl": "u"}},
        ], on_progress=lambda done, total: seen.append((done, total)))
        self.assertEqual(seen, [(6, 105)])

    def test_running_without_extract_progress_does_not_crash(self):
        seen = []
        url = self.run_poll([
            {"jobId": "j1", "state": "running"},
            {"jobId": "j1", "state": "done", "resultUrl": {"jsonUrl": "u"}},
        ], on_progress=lambda done, total: seen.append((done, total)))
        self.assertEqual(url, "u")
        self.assertEqual(seen, [])

    def test_pending_does_not_report_progress(self):
        # 约定的 progress 只在 running 时报。少写 state == "running" 这一半，
        # pending 也带着 extractProgress 时会误报。本机没见过这种响应，但约定
        # 就是约定，钉住它。
        seen = []
        url = self.run_poll([
            {"jobId": "j1", "state": "pending",
             "extractProgress": {"extractedPages": 1, "totalPages": 2}},
            {"jobId": "j1", "state": "done", "resultUrl": {"jsonUrl": "u"}},
        ], on_progress=lambda done, total: seen.append((done, total)))
        self.assertEqual(url, "u")
        self.assertEqual(seen, [])

    def test_running_with_progress_but_no_callback_does_not_crash(self):
        # 同一处守卫的另一半。回调在签名里是可选的，默认就是 None——少写
        # `and on_progress`，没有回调的调用方会当场 TypeError，而正则跑到
        # 一半正好报进度的时候才炸。
        url = self.run_poll([
            {"jobId": "j1", "state": "running",
             "extractProgress": {"extractedPages": 6, "totalPages": 105}},
            {"jobId": "j1", "state": "done", "resultUrl": {"jsonUrl": "u"}},
        ])
        self.assertEqual(url, "u")

    def test_failed_carries_the_service_error_message(self):
        with self.assertRaises(JobFailed) as ctx:
            self.run_poll([{"jobId": "j1", "state": "failed",
                            "errorMsg": "解析失败：文件损坏"}])
        self.assertIn("文件损坏", str(ctx.exception))

    def test_failed_without_a_message_still_says_something(self):
        # 服务没给 errorMsg 时别让报错只有一个冒号。用户拿到的是
        # 「任务失败：」还是「任务失败：服务没说原因」，差别就在这一句。
        with self.assertRaises(JobFailed) as ctx:
            self.run_poll([{"jobId": "j1", "state": "failed"}])
        self.assertIn("服务没说原因", str(ctx.exception))

    def test_done_without_result_url_is_an_error(self):
        with self.assertRaises(JobFailed) as ctx:
            self.run_poll([{"jobId": "j1", "state": "done"}])
        self.assertIn("结果地址", str(ctx.exception))

    def test_unknown_state_is_an_error_not_an_endless_loop(self):
        with self.assertRaises(JobFailed) as ctx:
            self.run_poll([{"jobId": "j1", "state": "queued"}])
        self.assertIn("queued", str(ctx.exception))

    def test_200_with_a_non_json_body_is_an_error_not_a_crash(self):
        # 轮询这条路上网关回了 200 却不是 JSON：同 Task 7，别让 ValueError 漏出去
        resp = FakeResponse(status_code=200, text="<html>hello</html>")
        with mock.patch.object(requests, "get", lambda *a, **k: resp):
            with self.assertRaises(SubmitRejected) as ctx:
                aistudio.poll("j1", "t")
        self.assertIn("hello", str(ctx.exception))
        self.assertIn("轮询", str(ctx.exception))

    def test_200_with_a_nonzero_code_is_a_rejection_not_an_unknown_state(self):
        # submit 那条路早就防着「HTTP 200 但 code 非 0」，Task 7 钉过这是真形状。
        # 轮询这条路少写这一条，服务说「任务不存在」时会被说成
        # 「没见过的任务状态：None」——服务自己写的原因和 traceId 全丢了，
        # 使用者拿到的是一句误导人的诊断。
        resp = FakeResponse(body={"code": 10002, "msg": "任务不存在",
                                  "traceId": "tr-1"})
        with mock.patch.object(requests, "get", lambda *a, **k: resp):
            with self.assertRaises(SubmitRejected) as ctx:
                aistudio.poll("j1", "t")
        self.assertIn("10002", str(ctx.exception))
        self.assertIn("任务不存在", str(ctx.exception))
        self.assertIn("tr-1", str(ctx.exception))
        self.assertIn("轮询", str(ctx.exception))

    def test_a_transient_failure_does_not_kill_the_poll(self):
        # 轮询可能要跑几十分钟，中间抖一下不该让整份白等。循环里若不经过
        # _retry，网络类错误会当场穿出去，这一份就前功尽弃。
        calls = []

        def flaky(url, **kw):
            calls.append(1)
            if len(calls) < 3:
                raise requests.ConnectionError("抖了一下")
            return FakeResponse(body={"code": 0, "data": {
                "jobId": "j1", "state": "done",
                "resultUrl": {"jsonUrl": "u"}}})

        with mock.patch.object(requests, "get", flaky), \
             mock.patch.object(aistudio.time, "sleep", lambda s: None):
            self.assertEqual(aistudio.poll("j1", "t"), "u")
        self.assertEqual(len(calls), 3)


class TestFetch(unittest.TestCase):
    def test_jsonl_is_returned_as_text(self):
        resp = FakeResponse(text='{"errorCode":0}\n')
        resp.content = '{"errorCode":0}\n'.encode("utf-8")
        with mock.patch.object(requests, "get", lambda *a, **k: resp):
            self.assertEqual(aistudio.fetch_jsonl("https://x/r.jsonl"),
                             '{"errorCode":0}\n')

    def test_jsonl_is_decoded_as_utf8_not_by_guessing(self):
        # 对象存储常把 JSONL 当 text/plain 发，requests 对没有 charset 的
        # text/* 一律按 ISO-8859-1 解——中文会静默变成乱码。
        # 这里把 text 摆成乱码那份、content 摆成正确的字节，
        # 用 resp.text 的实现会红。
        raw = '{"errorCode":0,"msg":"文件格式不支持"}\n'.encode("utf-8")
        resp = FakeResponse(text=raw.decode("iso-8859-1"))
        resp.content = raw
        with mock.patch.object(requests, "get", lambda *a, **k: resp):
            self.assertEqual(aistudio.fetch_jsonl("https://x/r.jsonl"),
                             '{"errorCode":0,"msg":"文件格式不支持"}\n')

    def test_jsonl_non_200_is_a_job_failure(self):
        # 状态码不对不是瞬断，重试也没用。这条顺带把那句空口白话钉实：非 200
        # 只问一次。（原来这里挂了个 RETRY_DELAY=0 的补丁，可假响应是「返回」
        # 不是「抛」，_retry 第一轮就返回了，那个补丁从来没被读到。）
        tries = []

        def not_found(url, **kw):
            tries.append(url)
            return FakeResponse(status_code=404, text="gone")

        with mock.patch.object(requests, "get", not_found):
            with self.assertRaises(JobFailed) as ctx:
                aistudio.fetch_jsonl("https://x/r.jsonl")
        self.assertIn("404", str(ctx.exception))
        self.assertEqual(len(tries), 1)

    def test_image_bytes_are_returned(self):
        resp = FakeResponse(body=None, text="")
        resp.content = b"\xff\xd8\xff\xe0jpeg"
        with mock.patch.object(requests, "get", lambda *a, **k: resp):
            self.assertEqual(aistudio.fetch_image("https://x/a.jpg"),
                             b"\xff\xd8\xff\xe0jpeg")

    def test_expired_signature_raises_network_error(self):
        # 签名过期时图床返回 403；上层按「这张取不回来」处理，不中断整批。
        # 403 重试也没用，同样只问一次。
        tries = []

        def expired(url, **kw):
            tries.append(url)
            return FakeResponse(status_code=403, text="expired")

        with mock.patch.object(requests, "get", expired):
            with self.assertRaises(NetworkError) as ctx:
                aistudio.fetch_image("https://x/a.jpg")
        self.assertIn("403", str(ctx.exception))
        self.assertEqual(len(tries), 1)
        # 图床的网址带签名，取错了不会报错，只会取回一张废图或者 403，
        # 所以「地址就是传进去那个」也得钉一句
        self.assertEqual(tries[0], "https://x/a.jpg")

    def test_image_download_uses_a_shorter_retry_budget(self):
        self.assertLess(aistudio.IMAGE_RETRY_ATTEMPTS, aistudio.RETRY_ATTEMPTS)

    def test_image_download_hands_its_own_network_settings_down(self):
        # 上面那条只盯常量的数值。常量摆在那儿不等于取图这条路用上了它：把
        # attempts=/delay=/timeout= 删掉或换掉，上面那条照样绿，而实际行为会
        # 退回默认的 3 次 × 2 秒、900 秒超时——一张图挂住，一个 worker 就白
        # 占十几分钟。这条盯的是 fetch_image 真把它们传下去了。
        tries = []
        naps = []
        seen = {}

        def boom(url, **kw):
            tries.append(1)
            seen.update(kw)
            raise requests.ConnectionError("断了")

        with mock.patch.object(requests, "get", boom), \
             mock.patch.object(aistudio.time, "sleep", naps.append):
            with self.assertRaises(NetworkError) as ctx:
                aistudio.fetch_image("https://x/a.jpg")
        self.assertEqual(len(tries), aistudio.IMAGE_RETRY_ATTEMPTS)
        self.assertEqual(naps, [aistudio.IMAGE_RETRY_DELAY])
        self.assertEqual(seen["timeout"], aistudio.SMALL_TIMEOUT)
        # 重试耗尽的报错要指明是取图这一段，别让使用者以为是取结果
        self.assertIn("取图", str(ctx.exception))

    def test_jsonl_download_rides_out_a_transient_network_failure(self):
        # 加这条用例之前，前面几条给的响应都是一次就成，_retry 这一层整个
        # 没被走到：把它删掉、把标签换成「取图」、把重试次数钉成 1，一条都
        # 不红（现在这三条都红，红的就是这条用例）。少这一层的后果是取结果
        # 时碰上一次瞬断就抛出 requests 自己的异常，而它不在收尾的捕获表里
        # ——一份文件的失败会带走整批。
        tries = []
        naps = []

        def flaky(url, **kw):
            tries.append(url)
            if len(tries) == 1:
                raise requests.ConnectionError("断了")
            resp = FakeResponse(text='{"errorCode":0}\n')
            resp.content = '{"errorCode":0}\n'.encode("utf-8")
            return resp

        with mock.patch.object(requests, "get", flaky), \
             mock.patch.object(aistudio.time, "sleep", naps.append):
            out = aistudio.fetch_jsonl("https://x/r.jsonl")
        self.assertEqual(out, '{"errorCode":0}\n')
        self.assertEqual(len(tries), 2)          # 断一次、成一次
        self.assertEqual(naps, [aistudio.RETRY_DELAY])
        self.assertEqual(tries[0], "https://x/r.jsonl")

    def test_jsonl_gives_up_after_the_full_retry_budget(self):
        tries = []

        def boom(url, **kw):
            tries.append(url)
            raise requests.ConnectionError("断了")

        with mock.patch.object(requests, "get", boom), \
             mock.patch.object(aistudio.time, "sleep", lambda s: None):
            with self.assertRaises(NetworkError) as ctx:
                aistudio.fetch_jsonl("https://x/r.jsonl")
        self.assertEqual(len(tries), aistudio.RETRY_ATTEMPTS)
        # 试满次数仍不通，报错要指明是取结果这一段，别让人以为是取图
        self.assertIn("取结果", str(ctx.exception))

    def test_jsonl_eats_a_byte_order_mark(self):
        # 对象存储偶尔在开头塞 BOM。留着它，第一行的 json.loads 就解不动，
        # 一份本来好好的结果从第一行起整份作废。
        resp = FakeResponse(text="")
        # 显式写出 BOM 的三个字节，别用 '\ufeff' 那种转义：那个字符在编辑器里
        # 是隐形的，一旦在哪一环被吃掉，这条用例就退化成「没有 BOM」，而它
        # 照样绿——测的东西没了，谁也不知道。
        resp.content = b"\xef\xbb\xbf" + '{"errorCode":0}\n'.encode("utf-8")
        with mock.patch.object(requests, "get", lambda *a, **k: resp):
            self.assertEqual(aistudio.fetch_jsonl("https://x/r.jsonl"),
                             '{"errorCode":0}\n')


class TestCheckDependencies(unittest.TestCase):
    def test_nothing_missing_when_all_three_are_installed(self):
        self.assertEqual(convert.missing_dependencies(), [])

    def test_names_what_is_missing(self):
        self.assertEqual(
            convert.missing_dependencies(("requests", "这个包肯定没有")),
            ["这个包肯定没有"])

    def test_missing_dependency_exits_with_the_uv_command_line(self):
        with self.assertRaises(SystemExit) as ctx:
            convert.check_dependencies(("这个包肯定没有",))
        message = str(ctx.exception)
        self.assertIn("这个包肯定没有", message)
        self.assertIn("uv run --with requests --with lxml --with tabulate", message)


class TestOutputDirName(unittest.TestCase):
    def test_local_path_uses_the_file_stem(self):
        self.assertEqual(convert.output_dir_name("/a/b/报告 v2.pdf"), "报告 v2")

    def test_url_drops_query_and_extension(self):
        self.assertEqual(
            convert.output_dir_name("https://x/y/dummy.pdf?authorization=abc"),
            "dummy")

    def test_url_without_pdf_extension(self):
        self.assertEqual(convert.output_dir_name("https://x/y/report"), "report")

    def test_url_with_percent_escapes(self):
        self.assertEqual(convert.output_dir_name("https://x/y/%E6%8A%A5%E5%91%8A.pdf"),
                         "%E6%8A%A5%E5%91%8A")

    def test_trailing_slash_url_falls_back(self):
        self.assertEqual(convert.output_dir_name("https://x/y/"), "y")

    def test_signed_url_with_a_dot_in_the_query_still_drops_the_query(self):
        # 对象存储的签名网址 query 里带点是常态（`?auth=abc.def`）。不剥 query
        # 切出来的是 `a.pdf?auth=abc`——里面那个 `?` 在 Windows 上根本建不出目录。
        self.assertEqual(
            convert.output_dir_name("https://x/y/a.pdf?auth=abc.def"), "a")

    def test_bare_domain_falls_back_to_the_host(self):
        # 路径是空的，`last` 取不出东西，只能退回主机名
        self.assertEqual(convert.output_dir_name("https://x.example.com/"),
                         "x.example")


class TestCollectInputs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name

    def write(self, rel, content="%PDF-1.4\n"):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_directory_is_scanned_recursively_for_pdfs_only(self):
        self.write("a.pdf")
        self.write("sub/b.pdf")
        self.write("sub/note.txt")
        tasks = convert.collect_inputs([self.root])
        self.assertEqual(sorted(t.name for t in tasks), ["a", "b"])

    def test_one_file_given_twice_becomes_one_task(self):
        path = self.write("a.pdf")
        self.assertEqual(len(convert.collect_inputs([path, path])), 1)

    def test_a_url_is_passed_through_untouched(self):
        # 网址不能像本地路径那样过一遍 abspath：那会把它拼成本机上的一个相对
        # 路径，交给服务端只会得到「文件不存在」。同一个网址给两次也只算一份。
        url = "https://x/y/a.pdf"
        tasks = convert.collect_inputs([url, url])
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].target, url)
        self.assertEqual(tasks[0].name, "a")

    def test_two_urls_differing_only_in_case_are_two_tasks(self):
        # 网址去重比的是字符串本身，不走本地那条 normcase 归一——网址的路径
        # 是分大小写的，归一之后这两条会被当成同一份，悄悄少转一个。
        # （这条只在 Windows 上抓得住：折大小写的是 ntpath 的 normcase，不是
        # 文件系统——macOS 默认卷也不区分大小写，可它走 posixpath，照样抓不住。）
        one = "https://x/y/a.pdf"
        two = "https://x/y/A.pdf"
        tasks = convert.collect_inputs([one, two])
        self.assertEqual([t.target for t in tasks], [one, two])

    def test_same_name_from_two_directories_gets_two_output_dirs(self):
        one = self.write("x/report.pdf")
        two = self.write("y/report.pdf")
        # 改名这一步会往 stderr 说一声，不接住就喷进测试输出里，把
        # 「几条通过几条失败」那一行冲散——照 TestParseArgs 那套接住
        err = io.StringIO()
        with mock.patch.object(sys, "stderr", err):
            tasks = convert.collect_inputs([one, two])
        self.assertEqual(sorted(t.name for t in tasks), ["report", "report-2"])
        self.assertIn("report-2", err.getvalue())

    def test_a_file_named_like_a_url_is_still_a_local_file(self):
        # `startswith("http")` 会把一个真名叫 `http_notes.pdf` 的本地文件认成
        # 网址：路径压根不被 stat，那个字符串被原样当成网址丢给服务端，报回来
        # 的错跟「文件明明在」完全对不上。本地输入一律回绝对路径。
        self.write("http_notes.pdf")
        old = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, old)
        tasks = convert.collect_inputs(["http_notes.pdf"])
        self.assertEqual(tasks[0].target, os.path.abspath("http_notes.pdf"))

    def test_a_directory_named_like_a_pdf_is_not_collected(self):
        # 目录名以 .pdf 结尾时 rglob 会把它一起收进来，交给 submit 必炸。
        # 判据是「是不是文件」，不是「名字像不像」。
        self.write("d/real.pdf")
        os.makedirs(os.path.join(self.root, "d", "weird.pdf"))
        tasks = convert.collect_inputs([os.path.join(self.root, "d")])
        self.assertEqual([t.name for t in tasks], ["real"])

    def test_empty_directory_is_an_error(self):
        with self.assertRaises(SystemExit) as ctx:
            convert.collect_inputs([self.root])
        self.assertIn("没找到", str(ctx.exception))

    def test_missing_path_is_an_error(self):
        with self.assertRaises(SystemExit) as ctx:
            convert.collect_inputs([os.path.join(self.root, "nope.pdf")])
        self.assertIn("找不到", str(ctx.exception))


class TestParseArgs(unittest.TestCase):
    def output(self, name="out"):
        """给一个不存在的输出路径。

        写死相对路径 "out" 是跟工作目录较劲：parse_args 有一句「--output
        已经是个文件就报错」，当前目录下真有叫 out 的文件时，这两条用例会在
        断言之前就抛 SystemExit(2) 出来。
        """
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return os.path.join(tmp.name, name)

    def test_output_is_required(self):
        # 同下面两条：argparse 的 usage 与报错是写 stderr 的，这里要接住，
        # 否则它直接喷进测试输出里，把整套输出弄脏
        err = io.StringIO()
        with mock.patch.object(sys, "stderr", err), \
             self.assertRaises(SystemExit) as ctx:
            convert.parse_args(["a.pdf"])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("--output", err.getvalue())

    def test_defaults(self):
        args = convert.parse_args(["a.pdf", "--output", self.output()])
        self.assertEqual(args.model, aistudio.DEFAULT_MODEL)
        self.assertEqual(args.jobs, 4)
        self.assertFalse(args.force)

    def test_jobs_must_be_at_least_one(self):
        # argparse 的 parser.error 是先把消息写进 stderr、再 sys.exit(2)，
        # 异常本身只带退出码，所以消息要去 stderr 里取，不在异常上
        err = io.StringIO()
        with mock.patch.object(sys, "stderr", err), \
             self.assertRaises(SystemExit) as ctx:
            convert.parse_args(["a.pdf", "--output", self.output(), "--jobs", "0"])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("jobs", err.getvalue())

    def test_output_must_not_be_an_existing_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            self.addCleanup(os.remove, f.name)
            err = io.StringIO()
            with mock.patch.object(sys, "stderr", err), \
                 self.assertRaises(SystemExit) as ctx:
                convert.parse_args(["a.pdf", "--output", f.name])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("目录", err.getvalue())


class TestAlreadyDone(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name

    def touch_md(self, name):
        d = os.path.join(self.root, name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{name}.md"), "w", encoding="utf-8") as f:
            f.write("x")

    def test_missing_md_means_not_done(self):
        self.assertFalse(convert.already_done(self.root, "a"))

    def test_a_leftover_directory_without_the_md_is_not_done(self):
        # 上一趟跑到建目录那一步就断了、md 还没落盘，是常见的中间状态——
        # 目录在、md 不在。判据要是「目录在不在」，这一份就会被当成转过了
        # 跳过，而且屏幕上不会留下任何痕迹：使用者只会发现这份不见了。
        os.makedirs(os.path.join(self.root, "a", "images"), exist_ok=True)
        self.assertFalse(convert.already_done(self.root, "a"))

    def test_existing_md_means_done_regardless_of_source_mtime(self):
        self.touch_md("a")
        self.assertTrue(convert.already_done(self.root, "a"))


class TestConvertOne(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name

    def fake_pipeline(self, pages, fail_images=()):
        """把网络那一段整个换掉，只跑编排和落盘。"""
        # jsonl_line 造的是**一行**（一行里可以有好几页），别把它整个拿去 join
        # ——对字符串做 join 会把它的每个字符拆开，parse_jsonl 第一行就报不是 JSON
        raw = "\n".join(jsonl_line([p]) for p in pages)

        # 四个替身各自把收到的实参记下来：光按名字换掉替身的话实参一律不看，
        # 「位置写反」「传错变量」这类错整套一条不红（实测过）。
        self.calls = []

        def fake_submit(target, model, token):
            self.calls.append(("submit", (target, model, token)))
            return "j1"

        def fake_poll(job_id, token, on_progress=None):
            self.calls.append(("poll", (job_id, token)))
            if on_progress:
                on_progress(len(pages), len(pages))
            return "https://x/r.jsonl"

        def fake_fetch_image(url):
            self.calls.append(("fetch_image", (url,)))
            if url in fail_images:
                raise aistudio.NetworkError("图床返回 HTTP 403")
            return b"\xff\xd8\xff\xe0jpeg"

        def fake_fetch_jsonl(url):
            self.calls.append(("fetch_jsonl", (url,)))
            return raw

        return mock.patch.multiple(
            aistudio,
            submit=fake_submit, poll=fake_poll,
            fetch_jsonl=fake_fetch_jsonl, fetch_image=fake_fetch_image)

    def test_writes_md_and_images(self):
        task = convert.Task(target="/tmp/a.pdf", name="a", origin="/tmp/a.pdf")
        pages = [("正文一", {}),
                 ('正文二\n\n<img src="imgs/x.jpg">',
                  {"imgs/x.jpg": "https://x/1/x.jpg"})]
        with self.fake_pipeline(pages):
            result = convert.convert_one(task, self.root, "m", "t")
        md = os.path.join(self.root, "a", "a.md")
        self.assertTrue(os.path.isfile(md))
        with open(md, encoding="utf-8") as f:
            # 落盘时正文末尾补一个换行
            self.assertEqual(f.read(), "正文一\n\n正文二\n\n![](images/x.jpg)\n")
        self.assertTrue(os.path.isfile(os.path.join(self.root, "a", "images", "x.jpg")))
        # 只验「文件在」不够：`open(..., "wb")` 本身就会把文件建出来，写不写
        # 字节它都在。实测把这行的下一句去掉之后，往图片里写空字节、写错字节、
        # 只写一半，整套**一条不红**——而 md 里那句 ![](images/x.jpg) 照样
        # 指着它，使用者看到的是一张裂图，屏幕上一点提示都没有。
        with open(os.path.join(self.root, "a", "images", "x.jpg"), "rb") as f:
            self.assertEqual(f.read(), b"\xff\xd8\xff\xe0jpeg")
        self.assertEqual(result.pages, 2)
        self.assertEqual(result.missing_images, [])

    def test_the_four_network_calls_get_the_right_arguments(self):
        # 替身是照名字挂上去的，实参一个不看。实测过三处全绿：把 task.target
        # 写成 task.name（提交一份不存在的文件）、把 model 和 token 对调（拿
        # token 当模型名发出去）、把 poll 的 job_id 和 token 对调（拿别人的
        # 任务号去问状态）。三种都不是当场炸，是安静地做错事。这条把四个调用
        # 的实参逐个钉住。
        task = convert.Task(target="/tmp/a.pdf", name="a", origin="/tmp/a.pdf")
        pages = [('正文\n\n<img src="imgs/x.jpg">',
                  {"imgs/x.jpg": "https://x/1/x.jpg"})]
        with self.fake_pipeline(pages):
            convert.convert_one(task, self.root, "m", "t")
        self.assertEqual(self.calls, [
            ("submit", ("/tmp/a.pdf", "m", "t")),
            ("poll", ("j1", "t")),
            ("fetch_jsonl", ("https://x/r.jsonl",)),
            ("fetch_image", ("https://x/1/x.jpg",)),
        ])

    def test_no_pages_at_all_is_an_error(self):
        task = convert.Task(target="/tmp/a.pdf", name="a", origin="/tmp/a.pdf")
        with self.fake_pipeline([]):
            with self.assertRaises(convert.EmptyDocument) as ctx:
                convert.convert_one(task, self.root, "m", "t")
        self.assertIn("一页都没解析出来", str(ctx.exception))
        self.assertFalse(os.path.exists(os.path.join(self.root, "a", "a.md")))

    def test_missing_image_does_not_fail_the_document(self):
        task = convert.Task(target="/tmp/a.pdf", name="a", origin="/tmp/a.pdf")
        pages = [('正文\n\n<img src="imgs/x.jpg">',
                  {"imgs/x.jpg": "https://x/1/x.jpg"})]
        with self.fake_pipeline(pages, fail_images={"https://x/1/x.jpg"}):
            result = convert.convert_one(task, self.root, "m", "t")
        with open(os.path.join(self.root, "a", "a.md"), encoding="utf-8") as f:
            body = f.read()
        # 引用保持原样指向本地名，不加注释、不留远程地址
        self.assertEqual(body, "正文\n\n![](images/x.jpg)\n")
        self.assertEqual(result.missing_images, ["x.jpg"])
        self.assertFalse(os.path.exists(os.path.join(self.root, "a", "images", "x.jpg")))

    def test_md_is_written_with_lf_not_crlf(self):
        """Windows 上默认会写成 CRLF，落盘的 md 必须只有 LF。"""
        task = convert.Task(target="/tmp/a.pdf", name="a", origin="/tmp/a.pdf")
        with self.fake_pipeline([("正文", {})]):
            convert.convert_one(task, self.root, "m", "t")
        with open(os.path.join(self.root, "a", "a.md"), "rb") as f:
            blob = f.read()
        self.assertNotIn(bytes([13]), blob)

    def test_progress_callback_gets_page_counts(self):
        task = convert.Task(target="/tmp/a.pdf", name="a", origin="/tmp/a.pdf")
        seen = []
        with self.fake_pipeline([("一", {}), ("二", {})]):
            convert.convert_one(task, self.root, "m", "t",
                                on_pages=lambda d, t: seen.append((d, t)))
        self.assertEqual(seen, [(2, 2)])


class TestFormatDuration(unittest.TestCase):
    def test_seconds(self):
        self.assertEqual(convert.format_duration(9), "0:09")

    def test_minutes(self):
        self.assertEqual(convert.format_duration(125), "2:05")

    def test_hours(self):
        self.assertEqual(convert.format_duration(3725), "1:02:05")


class TestDisplayWidth(unittest.TestCase):
    def test_wide_characters_take_two_columns(self):
        # 清行时按它算要打多少空格才能把上一行整个盖掉。中日韩字符按一格
        # 算的话，中文文件名那一行会被清得短一截，上一行的尾巴就留在屏幕上。
        self.assertEqual(convert._display_width("abc"), 3)
        self.assertEqual(convert._display_width("中文"), 4)
        self.assertEqual(convert._display_width("a中"), 3)
        # 全角形式的西文字母（Ｆ 这一类）也算两格，别只认中日韩那几个区
        self.assertEqual(convert._display_width("Ａ"), 2)


class TestProgress(unittest.TestCase):
    def make(self, total=2):
        buf = io.StringIO()
        return buf, convert.Progress(total, stream=buf)

    def test_a_worker_thread_waits_for_the_lock_before_redrawing(self):
        """好几个任务同时想改那一行动态进度，谁也不能插到别人中间。

        不等的话，工作线程的 `add` 会在主线程正迭代 `inflight` 的半路往里
        塞一个键——那是 `RuntimeError: dictionary changed size during
        iteration`，而且是在屏幕上乱串字符之后才炸。
        """
        buf, p = self.make()
        p.add("a")
        real_lock = p.lock
        entered = threading.Event()
        done = []

        class TracedLock:
            """真锁外面套一层，只为在「准备抢锁」那一刻报个信。

            信在 acquire() **之前**报，所以等到信就说明这个线程下一步必然
            是抢锁——否则只能靠 sleep 猜它走到哪儿了。
            """

            def __enter__(self):
                entered.set()
                real_lock.acquire()
                return self

            def __exit__(self, *exc):
                real_lock.release()
                return False

        p.lock = TracedLock()

        def worker():
            p.pages("a", 1, 2)
            done.append(1)

        # 主线程直接拿真锁（不走 TracedLock），于是那个信只可能是工作线程报的
        real_lock.acquire()
        try:
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            # 信是在 acquire() **之前**报的，所以等到信就说明工作线程已经站在
            # 抢锁那一格上了；锁在主线程手里，它过不去。下面两条断言因此是
            # **必然**成立的，不用 sleep 去等——等出来的只是让测试变慢。
            self.assertTrue(entered.wait(5), "工作线程没走到抢锁那一步")
            self.assertEqual(done, [])
            self.assertEqual(p.inflight["a"], (None, None))
        finally:
            real_lock.release()
        thread.join(timeout=5)
        self.assertEqual(done, [1])
        self.assertIn("1/2 页", buf.getvalue())   # 放行之后照画不误

    def test_done_line_names_the_file_pages_and_time(self):
        buf, p = self.make()
        p.add("a")
        p.done_line(convert.Result(name="a", pages=105, seconds=84.9,
                                   missing_images=[]))
        text = buf.getvalue()
        self.assertIn("a", text)
        self.assertIn("105 页", text)
        self.assertIn("1:24", text)

    def test_done_line_mentions_missing_images(self):
        buf, p = self.make()
        p.done_line(convert.Result(name="a", pages=1, seconds=1.0,
                                   missing_images=["x.jpg", "y.jpg"]))
        self.assertIn("缺 2 张图", buf.getvalue())

    def test_skipped_lines_are_reported(self):
        buf, p = self.make()
        p.note("跳过 a（已经转过）")
        self.assertIn("跳过 a", buf.getvalue())


class TestRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        # run() 的进度行走在 stderr 上、末尾那两段汇总走在 stdout 上。不接住的话
        # 它们会混进测试运行输出里，而且没法断言。unittest 自己的报告不受影响：
        # runner 在构造时就把真正的 stderr 存下来了，这里换的是模块属性。
        self.out = io.StringIO()
        for name in ("stdout", "stderr"):
            patcher = mock.patch("sys." + name, self.out)
            patcher.start()
            self.addCleanup(patcher.stop)
        # run() 一开头会去拿 token；测试里不发请求，直接换掉
        patcher = mock.patch.object(aistudio, "get_token", lambda: "t")
        patcher.start()
        self.addCleanup(patcher.stop)

    def args(self, **kw):
        base = dict(output=self.root, model="m", force=False, jobs=2)
        base.update(kw)
        return argparse.Namespace(**base)

    def test_successful_run_exits_zero(self):
        tasks = [convert.Task(target="/tmp/a.pdf", name="a", origin="a")]
        with mock.patch.object(convert, "convert_one",
                              lambda *a, **k: convert.Result("a", 1, 0.1, [])):
            self.assertEqual(convert.run(tasks, self.args()), 0)
        # 那一行动态进度是这东西唯一的存在理由，完成数不累加它就永远显示 0
        self.assertIn("1/1 完成", self.out.getvalue())

    def test_a_failing_file_does_not_stop_the_others(self):
        tasks = [convert.Task(target="/tmp/a.pdf", name="a", origin="a"),
                 convert.Task(target="/tmp/b.pdf", name="b", origin="b")]

        def flaky(task, *a, **k):
            if task.name == "a":
                raise aistudio.JobFailed("解析失败：文件损坏")
            return convert.Result("b", 1, 0.1, [])

        with mock.patch.object(convert, "convert_one", flaky):
            self.assertEqual(convert.run(tasks, self.args()), 1)
        # 末尾那段汇总得点名是哪一份、为什么——只返回 1 不够，用户要的是线索。
        # 缩进两个空格才钉得住汇总里那行：进度行的 note 也会打同一句话，
        # 不缩进、前面还带「失败」两个字。
        text = self.out.getvalue()
        self.assertIn("1 份失败", text)
        self.assertIn("\n  a：解析失败：文件损坏", text)
        self.assertIn("失败 1", text)      # 动态进度行里也记了这一笔

    def test_a_local_error_only_fails_that_one_file(self):
        # 本机的问题（源文件读不出来、盘写满了）不是服务那边的事，但也只该
        # 让这一份失败。捕获表里少写 OSError，一份读不出来的文件就把整批带走。
        tasks = [convert.Task(target="/tmp/a.pdf", name="a", origin="a"),
                 convert.Task(target="/tmp/b.pdf", name="b", origin="b")]
        got = []

        def flaky(task, *a, **k):
            if task.name == "a":
                raise OSError("读不出来")
            got.append(task.name)
            return convert.Result("b", 1, 0.1, [])

        with mock.patch.object(convert, "convert_one", flaky):
            self.assertEqual(convert.run(tasks, self.args()), 1)
        self.assertEqual(got, ["b"])      # 另一份照跑完了
        self.assertIn("\n  a：读不出来", self.out.getvalue())

    def test_every_listed_failure_keeps_the_batch_alive(self):
        # run() 那张捕获表列了六种「只该让这一份失败」的异常。少写哪一种，
        # 哪一种就会穿出去把整批带走——一条一条地试，别只挑一个有代表性的。
        cases = [aistudio.SubmitRejected(500, msg="x"),
                 aistudio.JobFailed("x"),
                 aistudio.NetworkError("x"),
                 convert.EmptyDocument("x"),
                 JsonlLineError("x"),
                 OSError("x")]
        for exc in cases:
            with self.subTest(exc=type(exc).__name__):
                tasks = [convert.Task(target="/tmp/a.pdf", name="a", origin="a"),
                         convert.Task(target="/tmp/b.pdf", name="b", origin="b")]

                def flaky(task, *a, _exc=exc, **k):
                    if task.name == "a":
                        raise _exc
                    return convert.Result("b", 1, 0.1, [])

                with mock.patch.object(convert, "convert_one", flaky):
                    self.assertEqual(convert.run(tasks, self.args()), 1)

    def test_missing_images_are_named_at_the_end(self):
        tasks = [convert.Task(target="/tmp/a.pdf", name="a", origin="a")]
        with mock.patch.object(convert, "convert_one",
                               lambda *a, **k: convert.Result(
                                   "a", 1, 0.1, ["x.jpg", "y.jpg"])):
            self.assertEqual(convert.run(tasks, self.args()), 0)
        text = self.out.getvalue()
        self.assertIn("有图没取回来", text)
        self.assertIn("\n  a：x.jpg、y.jpg", text)

    def test_completions_are_reported_as_they_finish_not_in_submission_order(self):
        """谁先转完谁先报——那一行动态进度条的全部价值就在这儿。

        这条得让两头都真起来：假池子给的是当场就算完的 Future，而
        `as_completed` 对一堆**已经完成**的 Future 是随便挑着吐的（实测三次
        跑出三种序），那种假池子上「按提交序」和「按完成序」根本看不出差别。
        这里让提交序和完成序**相反**（先提交的最慢），并且拿主线程自己的
        报账动作当闸门——每报完一个才放行下一个——于是不用 sleep 也是确定的。
        """
        submitted = ["slow", "mid", "fast"]       # 提交序：最慢的排在最前
        finished = ["fast", "mid", "slow"]        # 完成序：正好倒过来
        tasks = [convert.Task(target=f"/tmp/{n}.pdf", name=n, origin=n)
                 for n in submitted]
        futures = {n: Future() for n in submitted}
        gate = threading.Semaphore(0)
        reported = []

        class GatedPool:
            """交出去的是没完成的 Future，由 feeder 线程按指定顺序完成。"""

            def __init__(self, max_workers=None):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def submit(self, fn, *a, **k):
                return futures[a[0].name]

        def feeder():
            for name in finished:
                futures[name].set_result(convert.Result(name, 1, 0.1, []))
                # 等主线程把这一个报出来，再放行下一个。超时只是兜底：
                # 正确实现下这个等待是零长度的，真等满说明主线程卡住了。
                gate.acquire(timeout=5)

        real_done_line = convert.Progress.done_line

        def spy(progress, result):
            reported.append(result.name)
            real_done_line(progress, result)
            gate.release()

        thread = threading.Thread(target=feeder, daemon=True)
        with mock.patch.object(convert, "ThreadPoolExecutor", GatedPool), \
             mock.patch.object(convert.Progress, "done_line", spy):
            thread.start()
            convert.run(tasks, self.args(jobs=3))
        thread.join(timeout=5)
        # 换成「按提交序遍历 futures」，主线程会卡在第一份（最慢的、还没完成）
        # 上，直到它完成才一次把三行全吐出来——屏幕上就是长时间不动、然后三行
        # 一起蹦出来。
        self.assertEqual(reported, finished)

    def test_jobs_is_passed_to_the_pool(self):
        """--jobs 得真传下去；不传的话这个开关就是个摆设。"""
        seen = {}

        class RecordingPool:
            def __init__(self, max_workers=None):
                seen["max_workers"] = max_workers

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def submit(self, fn, *a, **k):
                # 真 Future、当场算完：这样 as_completed 不用跟着一起 mock
                future = Future()
                try:
                    future.set_result(fn(*a, **k))
                except BaseException as exc:
                    future.set_exception(exc)
                return future

        tasks = [convert.Task(target="/tmp/a.pdf", name="a", origin="a")]
        with mock.patch.object(convert, "ThreadPoolExecutor", RecordingPool), \
             mock.patch.object(convert, "convert_one",
                               lambda *a, **k: convert.Result("a", 1, 0.1, [])):
            convert.run(tasks, self.args(jobs=3))
        self.assertEqual(seen["max_workers"], 3)

    def test_already_converted_files_are_skipped_unless_forced(self):
        os.makedirs(os.path.join(self.root, "a"))
        with open(os.path.join(self.root, "a", "a.md"), "w", encoding="utf-8") as f:
            f.write("x")
        tasks = [convert.Task(target="/tmp/a.pdf", name="a", origin="a")]
        calls = []
        with mock.patch.object(convert, "convert_one",
                              lambda *a, **k: calls.append(1)):
            convert.run(tasks, self.args())
            self.assertEqual(calls, [])
            # 跳过得说出来。用户看到「什么都没发生」会以为工具坏了
            self.assertIn("跳过 a", self.out.getvalue())
            self.assertIn("跳过 1", self.out.getvalue())

        def counted(*a, **k):
            calls.append(1)
            return convert.Result("a", 1, 0.1, [])

        with mock.patch.object(convert, "convert_one", counted):
            convert.run(tasks, self.args(force=True))
        # 加了 --force 就得真去转
        self.assertEqual(len(calls), 1)

    def test_an_all_skipped_run_never_asks_for_a_token(self):
        # 全都已经转过时那一趟根本不用 token。真去拿的话，手里没有 token 的人
        # 会被一句「环境里没有 …」挡回来——他要的只是确认「都转过了」。
        os.makedirs(os.path.join(self.root, "a"), exist_ok=True)
        with open(os.path.join(self.root, "a", "a.md"), "w",
                  encoding="utf-8") as f:
            f.write("x")
        tasks = [convert.Task(target="/tmp/a.pdf", name="a", origin="a")]

        def boom():
            raise AssertionError("全跳过的一趟不该去拿 token")

        with mock.patch.object(aistudio, "get_token", boom):
            self.assertEqual(convert.run(tasks, self.args()), 0)
        self.assertIn("跳过 a", self.out.getvalue())


class TestMain(unittest.TestCase):
    def test_an_environment_problem_becomes_exit_2(self):
        """缺依赖、目录里没有 PDF、缺 token 都走这条路。

        它们抛的都是带字符串的 SystemExit；main 负责把它印出来并回一个
        退出码 2，好让调用方分得清「用法/环境不对」和「有文件没转成」。
        """
        err = io.StringIO()
        # --output 得指向一个不存在的路径：parse_args 见它已经是个文件就会
        # 直接 SystemExit(2) 出来，那条断言根本轮不到。
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = os.path.join(tmp.name, "out")
        with mock.patch.object(convert, "check_dependencies",
                               side_effect=SystemExit("缺依赖：lxml")), \
             mock.patch("sys.stderr", err):
            self.assertEqual(convert.main(["--output", out, "a.pdf"]), 2)
        self.assertIn("缺依赖：lxml", err.getvalue())


if __name__ == "__main__":
    unittest.main()
