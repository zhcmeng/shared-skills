#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""count_tokens.py 自己的测试。

    bash tests/run.sh token-counter
    python -X utf8 tests/token-counter/test_count_tokens.py

用例是从产出目录 evals/token-counter/test-case-design/ 那几份文档逐条落下来的：
方法名里的 TC 编号就是「测试用例规格说明」里的编号，样本按「测试数据需求」的
DATA 编号建，跑法按「测试规程规格说明」的四条规程分组。**类名与方法名照那几份
文档的「英文名」栏取**，改名字先改文档、再照抄回来，两边别各叫各的。

编号一位不差地照抄：代码里写不成连字符就换成下划线（`TC-30` 写成 `TC_30`），
不补零、不写成范围——一条一个号，拿着文档里的编号来搜，要能搜到。每条用例的
说明里写着它覆盖了哪几条覆盖项（TCOV-），对的是「覆盖项 ↔ 用例」那张表。

四组对四条规程，也对着四门技术建的那几个模型：

    TestMainScenarioAndInputChannels  TP-1，TM-3 的判定规则与 TM-5 的端到端主场景
    TestTextContentAndCounting        TP-2，TM-1 的有效类
    TestInvalidInputAndBoundaries     TP-3，TM-1 的无效类、TM-2 的边界值，与依据没规定的那三处
    TestEngineReadinessPaths          TP-4，TM-4 的引擎判定规则

两处与文档不是逐字对应，都是有意的（照哪条决策这么落的，编号写在每段末尾）：

一、TC-22、TC-23、TC-24、TC-25 那四条，文档按 ENV-5、ENV-6、ENV-7 的环境写走——
    新建一个干净环境、真的装一次、真的断网。这几样一次就是几十秒、还要连到软件源，
    放进每条都要跑的测试里只会被跳过、被当成偶发失败。这里测的是同一张判定表的
    判定与动作：把测试项导进来，替掉「本机能不能导入引擎」「本地有没有 wheel」
    「装得上装不上」这三处外部条件，验它走哪条路、发出去的是什么命令。照 ENV-5、
    ENV-6、ENV-7 真走一遍那一层，按 TP-4 的启动栏另做一次。（DEC-34）

二、TC-15 在文档里的要求是「两条通道给出同一个数」，实测两条通道不一致——文件通道
    去掉开头的编码标记（2／4），字面文本通道给什么数什么（3／5），文档里两组实际值
    都写着。这里钉的是实测值：测试套件不该常红。文档里那条要求成不成立、要不要照它
    判缺陷，留给用户定口径；定了以后这条测试跟着改。（DEC-20）
"""

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
# 测试在仓库根 tests/ 下，脚本还在 plugin/skills/ 里，往上两层
SCRIPT = (HERE.parent.parent / "plugin" / "skills" / "token-counter"
          / "scripts" / "count_tokens.py")
sys.path.insert(0, str(SCRIPT.parent))
import count_tokens  # noqa: E402

BOM = b"\xef\xbb\xbf"

# 「测试数据需求」里的正文样本，按 DATA 编号取。字符数与 token 数见那份文档，
# 都按随包词表算出来，这里只放文本本身。
TEXTS = {
    "DATA-1": "你好，世界",
    "DATA-2": "The quick brown fox jumps over the lazy dog",
    "DATA-3": "中文和 English 混排",
    "DATA-4": "<｜end▁of▁sentence｜>",
    "DATA-5": "   \n\t\n  ",
    "DATA-7": "emoji 😀 与中文混排",
    "DATA-8": " hello world ",
    "DATA-16": "中",
    # 下面这一条开头那个看不见的字符是 U+FEFF（编码标记），照原样留着，别顺手删掉
    "DATA-17": "﻿中文测试",
}

# 文件类样本，按字节逐一定义——边界值那几条要的正是逐字节的样本。
# 键是「测试数据需求」里的编号，文件名跟着编号走；断言里一律用编号取（FILES["DATA-9"]），
# 文件名只在建工作区那一处用到。
FILES = {
    "DATA-6": ("代码样本.py", "def add(a, b):\n    return a + b\n".encode("utf-8")),
    "DATA-9": ("样本.md", ("# 标题 Demo\n\nThe quick brown fox jumps over the lazy dog\n"
                           "你好，世界\n").encode("utf-8")),
    "DATA-10": ("带标记.md", BOM + "中文测试".encode("utf-8")),
    "DATA-11": ("非UTF8.md", "中文测试".encode("gbk")),
    "DATA-12": ("空文件.md", b""),
    "DATA-13": ("只有标记.md", BOM),
    "DATA-14": ("截断标记.md", b"\xef\xbb"),
    "DATA-15": ("标记加一字.md", BOM + b"a"),
}


class CountTokensTestBase(unittest.TestCase):
    """ENV-1、ENV-2、ENV-3 摆齐（解释器与平台、随包词表、随包 wheel），加 ENV-4 那块可写的
    工作区：各样本文本文件按字节造好，原始技能目录不动。子进程按 ENV-8 的命令通道起，
    ENV-9 取三个流。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="token-counter-")
        cls.work = Path(cls._tmp.name)
        for name, raw in FILES.values():
            (cls.work / name).write_bytes(raw)
        # 目录样本：路径指向一个目录那一条（TC-13）用，不列进测试数据需求，按 DEC-13 写进用例的输入
        (cls.work / "样本目录").mkdir(exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def sample(self, data_id):
        """按「测试数据需求」的编号取工作区里那份样本文件的路径（DATA-6、DATA-9 至 DATA-15）。"""
        return str(self.work / FILES[data_id][0])

    def run_script(self, args, stdin_bytes=None):
        """ENV-9：标准输出、标准错误、退出码三样分别取到。"""
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        p = subprocess.run([sys.executable, str(SCRIPT)] + list(args),
                           input=stdin_bytes, capture_output=True, env=env)
        return (p.returncode,
                p.stdout.decode("utf-8", "replace").replace("\r\n", "\n"),
                p.stderr.decode("utf-8", "replace"))

    def assert_counts(self, args, tokens, chars, stdin_bytes=None):
        """有效输入：标准输出恰好两行、标准错误为空、退出码 0。

        标准错误为空这一条同时管着引擎判定规则 1（本机已经可以导入时不出安装提示，
        TCOV-32）：这几条跑的时候引擎都装好了。
        """
        rc, out, err = self.run_script(args, stdin_bytes)
        self.assertEqual(out, "tokens: %d\nchars: %d\n" % (tokens, chars))
        self.assertEqual(err, "", "标准错误上不该有东西，实际是：%r" % err)
        self.assertEqual(rc, 0)

    def assert_no_count(self, args, stdin_bytes=None):
        """无效输入：不给计数结果、标准错误上有提示、退出码非 0（TCOV-19）。

        措辞与退出码的具体取值依据没有规定，只钉这三件事。
        """
        rc, out, err = self.run_script(args, stdin_bytes)
        self.assertNotIn("tokens:", out)
        self.assertNotIn("chars:", out)
        self.assertNotEqual(err, "", "标准错误上应当留下提示")
        self.assertNotEqual(rc, 0, "退出码应当非 0")


class TestTextContentAndCounting(CountTokensTestBase):
    """TM-1 的有效类与计数口径（TP-2 的前半段）。"""

    def test_TC_1_cjk_literal_pins_chars_semantics(self):
        """TCOV-2、TCOV-16、TCOV-17、TCOV-18、TCOV-26、TCOV-32、TCOV-38：含中文的正文走
        `--text` 这一路，数出 tokens 与 chars 两行，chars 给字符数；引擎已经装好，不出安装提示。"""
        # chars 给 5（字符个数），不是 15（这段正文在 UTF-8 里占 15 字节）
        self.assert_counts(["--text", TEXTS["DATA-1"]], 3, 5)

    def test_TC_2_ascii_words_with_spaces(self):
        """TCOV-1：纯 ASCII 正文、词与词之间有空格。"""
        self.assert_counts(["--text", TEXTS["DATA-2"]], 9, 43)

    def test_TC_3_leading_cjk_then_ascii(self):
        """TCOV-3：正文以汉字开头、后面接 ASCII。"""
        # 改走兼容加载路径的写法会把这段数出 0 个 token
        self.assert_counts(["--text", TEXTS["DATA-3"]], 6, 14)

    def test_TC_4_official_special_token(self):
        """TCOV-4：正文里含官方词表的特殊 token（`<｜end▁of▁sentence｜>`）。"""
        # 被拆成多个 token 即判缺陷
        self.assert_counts(["--text", TEXTS["DATA-4"]], 1, 19)

    def test_TC_5_empty_stdin(self):
        """TCOV-5、TCOV-30：空正文（标准输入接得上、里面一个字符都没有）给 0 与 0。"""
        self.assert_counts([], 0, 0, stdin_bytes=b"")

    def test_TC_6_whitespace_only(self):
        """TCOV-6：正文只有空白字符。"""
        self.assert_counts(["--text", TEXTS["DATA-5"]], 3, 8)

    def test_TC_7_code_text(self):
        """TCOV-7：正文是代码文本，走文件通道（DATA-6 那份）。"""
        self.assert_counts([self.sample("DATA-6")], 12, 32)

    def test_TC_8_astral_plane_char(self):
        """TCOV-8：正文含补充平面上的字符（emoji）。"""
        # 13 个字符，这段正文在 UTF-8 里占 26 字节
        self.assert_counts(["--text", TEXTS["DATA-7"]], 9, 13)

    def test_TC_9_file_bom_not_counted(self):
        """TCOV-9：文件开头的编码标记 BOM 不计入正文（DATA-10 那份）。"""
        self.assert_counts([self.sample("DATA-10")], 2, 4)

    def test_TC_10_leading_trailing_spaces(self):
        """TCOV-10：正文首尾带空格。"""
        self.assert_counts(["--text", TEXTS["DATA-8"]], 3, 13)


class TestInvalidInputAndBoundaries(CountTokensTestBase):
    """TM-1 的无效类、TM-2 的边界值，外加依据没规定的那三处（TP-3）。"""

    def test_TC_11_file_not_utf8(self):
        """TCOV-11、TCOV-19、TCOV-28、TCOV-42：文件里的字节不是合法 UTF-8——不给计数行、
        在标准错误上留话、以非 0 状态结束。"""
        self.assert_no_count([self.sample("DATA-11")])

    def test_TC_12_missing_path(self):
        """TCOV-12、TCOV-19、TCOV-29：路径不存在。"""
        self.assert_no_count([str(self.work / "不存在的文件.md")])

    def test_TC_13_path_is_directory(self):
        """TCOV-13、TCOV-29：路径指向一个目录。"""
        self.assert_no_count([str(self.work / "样本目录")])

    def test_TC_14_stdin_not_utf8(self):
        """TCOV-14、TCOV-19、TCOV-31：标准输入里的字节不是合法 UTF-8。"""
        self.assert_no_count([], stdin_bytes=FILES["DATA-11"][1])

    def test_TC_15_same_bytes_two_channels(self):
        """TCOV-15：同一段字节经两条通道的数。文档里这条要求「两条通道给出同一个数」，实测不一致。

        文件通道按去掉开头编码标记之后的正文算（2／4），字面文本通道给什么数什么
        （3／5）——`utf-8-sig` 只在读文件那一路上生效。这里钉的是实测值，两组都
        验：只验其中一组，另一组改了也看不出来。
        """
        self.assert_counts(["--text", TEXTS["DATA-17"]], 3, 5)
        self.assert_counts([self.sample("DATA-10")], 2, 4)

    def test_TC_16_three_channels_agree(self):
        """TCOV-20、TCOV-27、TCOV-30、TCOV-39：同一段正文经三条通道（`--text`、文件、
        管道）算出的两个数相同；文件那一条走的是判定规则 2。"""
        text = TEXTS["DATA-1"]
        plain = self.work / "去标记副本.md"  # DATA-1 那段正文写成一个不带编码标记的文件
        plain.write_bytes(text.encode("utf-8"))
        self.assert_counts(["--text", text], 3, 5)
        self.assert_counts([str(plain)], 3, 5)
        self.assert_counts([], 3, 5, stdin_bytes=text.encode("utf-8"))

    def test_TC_17_empty_file(self):
        """TCOV-21：边界值——正文长度 0 个字符（DATA-12 那份空文件）。"""
        self.assert_counts([self.sample("DATA-12")], 0, 0)

    def test_TC_18_single_char(self):
        """TCOV-17、TCOV-22：边界值——正文长度 1 个字符；chars 给字符数，不是字节数。"""
        self.assert_counts(["--text", TEXTS["DATA-16"]], 1, 1)

    def test_TC_19_truncated_bom(self):
        """TCOV-23：边界值——文件开头 2 个字节，少一个字节的编码标记（DATA-14 那份）。"""
        self.assert_no_count([self.sample("DATA-14")])

    def test_TC_20_bom_only(self):
        """TCOV-24：边界值——文件开头正好一个完整的编码标记，后面没有正文（DATA-13 那份）。"""
        self.assert_counts([self.sample("DATA-13")], 0, 0)

    def test_TC_21_bom_plus_one_byte(self):
        """TCOV-25：边界值——编码标记后接一个字节（DATA-15 那份）。"""
        self.assert_counts([self.sample("DATA-15")], 1, 1)

    def test_TC_27_all_three_sources_given(self):
        """TCOV-43：依据没规定；本设计的读法是命令行给的先于标准输入、`--text` 先于文件路径。"""
        rc, out, _ = self.run_script(
            [self.sample("DATA-9"), "--text", TEXTS["DATA-1"]],
            stdin_bytes=TEXTS["DATA-1"].encode("utf-8"))
        self.assertEqual(out, "tokens: 3\nchars: 5\n", "应当取 --text 那一路")
        self.assertEqual(rc, 0)

    def test_TC_28_file_and_stdin_available(self):
        """TCOV-44：依据没规定；本设计的读法是文件路径先于标准输入。"""
        rc, out, _ = self.run_script(
            [self.sample("DATA-9")],
            stdin_bytes=TEXTS["DATA-1"].encode("utf-8"))
        self.assertEqual(out, "tokens: 19\nchars: 61\n", "应当取文件那一路")
        self.assertEqual(rc, 0)

    def test_TC_29_empty_path_string(self):
        """TCOV-45：依据没规定。空字符串与「没给路径」是同一个判断结果，会转去读标准输入——
        调用方本意是指一个文件、而那个变量为空时，测试项不报错，静默数出管道里的内容。
        """
        self.assert_counts([""], 3, 5, stdin_bytes=TEXTS["DATA-1"].encode("utf-8"))


class TestMainScenarioAndInputChannels(CountTokensTestBase):
    """TM-3 判定表的正路，加 TM-5 的端到端主场景（TP-1）。"""

    def test_TC_26_main_scenario_markdown_file(self):
        """TCOV-18、TCOV-27、TCOV-37：主场景——已经装好引擎的机器上数一个文件，
        走的是判定规则 2。"""
        self.assert_counts([self.sample("DATA-9")], 19, 61)


class TestEngineReadinessPaths(unittest.TestCase):
    """TC-22、TC-23、TC-24、TC-25：引擎从哪来的四条路，对着 TM-4 的判定规则（TP-4）。
    外部条件替掉了，理由见文件开头。"""

    WHEEL = Path("wheels/tokenizers-0.22.2-cp39-abi3-win_amd64.whl")

    def ensure(self, wheel, installed, runs):
        """跑一次 ensure_tokenizers，把发出去的安装命令记下来。

        installed：本机能不能导入引擎；runs：各次安装的返回码，按顺序取，异常按异常抛。
        """
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(list(cmd))
            outcome = runs.pop(0)
            if isinstance(outcome, BaseException):
                raise outcome
            return mock.Mock(returncode=outcome)

        err = io.StringIO()
        with mock.patch.object(count_tokens.importlib.util, "find_spec",
                               return_value=object() if installed else None), \
                mock.patch.object(count_tokens, "WHEEL", wheel), \
                mock.patch.object(count_tokens.subprocess, "run", side_effect=fake_run), \
                contextlib.redirect_stderr(err):
            count_tokens.ensure_tokenizers()
        return calls, err.getvalue()

    def test_TC_22_offline_bundled_wheel(self):
        """TCOV-33、TCOV-40：本机没装、随包 wheel 在且装得上时，离线装这个 wheel——
        没有引擎、不能联网的机器上首次使用就走这条。"""
        calls, err = self.ensure(self.WHEEL, installed=False, runs=[0])
        self.assertEqual(
            calls,
            [[sys.executable, "-m", "pip", "install", "--no-deps", "-q",
              str(self.WHEEL)]],
            "应当离线装随包的那个 wheel，不联网")
        self.assertNotEqual(err, "", "标准错误上应当留下安装提示")

    def test_TC_23_wheel_fails_then_pypi(self):
        """TCOV-34、TCOV-41：本机没装、随包 wheel 装不上、联网装得上时，转去联网装
        指定版本；机器上那个 wheel 不适用时首次使用就走这条。"""
        calls, err = self.ensure(self.WHEEL, installed=False, runs=[1, 0])
        self.assertEqual(len(calls), 2, "wheel 装不上时不该就此收手")
        self.assertEqual(
            calls[1],
            [sys.executable, "-m", "pip", "install", "-q",
             "tokenizers==" + count_tokens.PINNED])
        self.assertNotEqual(err, "")

    def test_TC_24_no_wheel_pypi_direct(self):
        """TCOV-35：本机没装、`wheels/` 下没有 wheel、联网装得上时，直接联网装指定版本。"""
        calls, _ = self.ensure(None, installed=False, runs=[0])
        self.assertEqual(
            calls,
            [[sys.executable, "-m", "pip", "install", "-q",
              "tokenizers==" + count_tokens.PINNED]])

    def test_TC_25_both_install_paths_fail(self):
        """TCOV-36：两条安装路都不通时，以非 0 状态结束，不产出计数两行。"""
        # 联网那条用的是 check=True，装不上就抛出来；main() 还没走到打印计数那一步，
        # 所以标准输出上不会有 tokens／chars 两行，进程以非 0 结束。
        with self.assertRaises(subprocess.CalledProcessError):
            self.ensure(None, installed=False,
                        runs=[subprocess.CalledProcessError(1, [])])


if __name__ == "__main__":
    unittest.main(verbosity=2)
