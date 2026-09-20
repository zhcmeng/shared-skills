import json
import os
import sys
import unittest
from unittest import mock

import requests

# 把 scripts/ 插进 sys.path，照 download-md-images 那份测试的写法
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import aistudio
from aistudio import NetworkError, SubmitRejected

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


class TestGetToken(unittest.TestCase):
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

        path = os.path.join(os.path.dirname(__file__), "fixture.pdf")
        with open(path, "wb") as f:
            f.write(b"%PDF-1.4\n")
        try:
            with mock.patch.object(requests, "post", fake_post):
                aistudio.submit(path, "PP-StructureV3", "t")
        finally:
            os.remove(path)
        self.assertNotIn("json", captured)
        self.assertEqual(captured["data"]["model"], "PP-StructureV3")
        self.assertIn("file", captured["files"])

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
        self.assertIn("502", str(ctx.exception))
        self.assertIn("Bad Gateway", str(ctx.exception))

    def test_code_nonzero_in_a_200_body_is_also_a_rejection(self):
        resp = FakeResponse(status_code=200, body={"code": 10002, "msg": "文件 URL 无法识别"})
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

        def boom(*a, **k):
            calls.append(1)
            raise requests.ConnectionError("getaddrinfo failed")

        with mock.patch.object(requests, "post", boom), \
             mock.patch.object(aistudio, "RETRY_DELAY", 0):
            with self.assertRaises(NetworkError) as ctx:
                aistudio.submit("https://example.com/a.pdf", "m", "t")
        self.assertEqual(len(calls), aistudio.RETRY_ATTEMPTS)
        self.assertIn("连不上", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
