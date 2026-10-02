#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""count_tokens.py 的测试：照 evals/token-counter/test-case-design/ 那几份规格落成。

    python tests/token-counter/test_count_tokens.py

**这是批一**——测试规程规格说明「各批落到哪」那一节里，TP-1（计数的三道输入与文本取值）
与 TP-2（首次运行的安装道）两条规程落成这一份能跑的测试代码：判据落在命令、标准输出、
退出码与盘上的文件上，跑一遍就有结论。TP-3 与 TP-4 那十条要读模型被调用时的表现，
归批二，落成评测用例，不在这一份里。

覆盖的编号（按「落成约定」照抄；函数名里那个连字符写成下划线，其余各处原样写连字符）：

  - TP-1 计数的三道输入与文本取值：TC-1、TC-2、TC-3、TC-4、TC-5、TC-6、TC-7、TC-8、
    TC-9、TC-10、TC-11、TC-12、TC-13、TC-14、TC-15、TC-16、TC-17、TC-18、TC-19、
    TC-20、TC-21
  - TP-2 首次运行的安装道：TC-22、TC-23、TC-24、TC-25
  - 模型：TM-1（等价类划分）、TM-2（边界值分析）、TM-3（判定表测试）；TM-4（场景测试）
    归批二
  - 覆盖项：TCOV-1、TCOV-2、TCOV-3、TCOV-4、TCOV-5、TCOV-6、TCOV-7、TCOV-8、TCOV-9、
    TCOV-10、TCOV-11、TCOV-12、TCOV-13、TCOV-14、TCOV-15、TCOV-16、TCOV-17、TCOV-18、
    TCOV-19、TCOV-20、TCOV-21、TCOV-27、TCOV-29、TCOV-30、TCOV-32、TCOV-33、TCOV-34、
    TCOV-35、TCOV-38、TCOV-39、TCOV-40、TCOV-41、TCOV-43、TCOV-44、TCOV-45、TCOV-46；
    TCOV-28、TCOV-31、TCOV-36、TCOV-37、TCOV-42 判为不可行（取值在 UTF-8 里造不出来、
    已从分母里剔除），照记在这儿；TCOV-22、TCOV-23、TCOV-24、TCOV-25、TCOV-26 与
    TCOV-47 至 TCOV-54 归批二
  - 数据项：DATA-1、DATA-2、DATA-3、DATA-4、DATA-5、DATA-6、DATA-7、DATA-8、DATA-9、
    DATA-10、DATA-11、DATA-12、DATA-13（DATA-14 与九条用户消息归批二）
  - 环境项：ENV-1、ENV-2、ENV-3、ENV-4、ENV-5、ENV-6、ENV-8（ENV-7 归批二）

**期望值一律照规格抄，不照脚本现在的输出抄。**这一份是拿规格判被测对象：脚本吐出来
的数与规格对不上，要报出来，不能反过来把规格改成脚本的样子——那这个测试就白写了。

**TC-18 至 TC-21 是记录型**：规格写明「依据未规定这一处」，它们记的是实现当下的行为
（两条道同时给时听谁的、走不通时怎么收场），拿规格里写死的取值当准头判；实现改了
这几条要重判。

**TC-24、TC-25 要联一次网**（ENV-6 可达是前提，由跑的人先保证）：它们把技能副本整个
复制到临时目录再改副本，测试项本身一个字都不动。
"""

import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKILL = REPO / "plugin" / "skills" / "token-counter"
SCRIPT = SKILL / "scripts" / "count_tokens.py"
WHEELS = SKILL / "wheels"

# 随技能打包的那份包：规则 2、3 要拿它的名字比版本、造坏文件
WHEEL = next(iter(WHEELS.glob("*.whl")), None)
PINNED = "0.22.2"  # 技能里钉住的引擎版本（联网那条道装的号）

BOM = b"\xef\xbb\xbf"

# 直接交给命令行的那几段文字，正文照测试数据需求那几栏取
TEXT_CJK = "你好，世界"                        # DATA-2 的正文（TC-1 走 --text）
TEXT_TWO_CJK = "你好"                          # TC-22、TC-24、TC-25 的输入
SPECIAL_TOKEN_TEXT = "<｜end▁of▁sentence｜>"   # DATA-8：19 个字符
ZERO_WIDTH_TEXT = "a" + chr(0x200B) + "b"       # DATA-9：a、零宽空格、b
BOM_CHAR_TEXT = chr(0xFEFF) + "你好"            # DATA-10：标记字符本身加两个汉字
CHAR_A = "a"                                   # DATA-11 之一，占 1 个字节
CHAR_E_ACUTE = chr(0xE9)                        # DATA-11 之一，U+00E9 预组合形，占 2 个字节
CHAR_CJK = "中"                                # DATA-11 之一，占 3 个字节
CHAR_EMOJI = "\U0001F600"                      # DATA-11 之一，U+1F600，占 4 个字节

# 摆成文件的那九条（DATA-1 至 DATA-7、DATA-12、DATA-13）；键是数据项编号，
# 值是（文件名, 字节）。字节照描述栏的十六进制写死——换个写法摆，字符数就对不上。
SAMPLES = {
    "DATA-1": ("ascii_file", b"hello world\n"),
    "DATA-2": ("chinese_file", TEXT_CJK.encode("utf-8")),
    "DATA-3": ("bom_file", BOM + TEXT_TWO_CJK.encode("utf-8")),
    "DATA-4": ("truncated_one_byte_file", b"\xef"),
    "DATA-5": ("truncated_two_bytes_file", b"\xef\xbb"),
    "DATA-6": ("surrogate_bytes_file", b"\xed\xa0\x80"),
    "DATA-7": ("control_chars_file", b"a\x00b"),
    "DATA-12": ("mixed_text_pipe", "你好 world 世界\n".encode("utf-8")),
    "DATA-13": ("replacement_file", b"\xef\xbf\xbd\xef\xbf\xbe"),
}


def run_script(args=(), stdin=b"", python=None, env=None, script=SCRIPT):
    """跑被测脚本，返回（退出码, 标准输出, 标准错误）。

    `python` 不给就用跑这一份测试的解释器（ENV-4）；`script` 不给就跑技能副本里那份
    （ENV-3），规则 3、4 那两条用例要跑改过的副本。
    """
    proc = subprocess.run(
        [python or sys.executable, str(script), *args],
        input=stdin, capture_output=True, env=env)
    return (proc.returncode,
            proc.stdout.decode("utf-8", "replace"),
            proc.stderr.decode("utf-8", "replace"))


@contextlib.contextmanager
def samples_dir():
    """按 TP-1 的「启动」把样本摆在同一个临时目录里（ENV-8）；跑完清掉。"""
    d = Path(tempfile.mkdtemp(prefix="tc-samples-"))
    try:
        paths = {}
        for data_id, (name, raw) in SAMPLES.items():
            p = d / name
            p.write_bytes(raw)
            paths[data_id] = p
        yield paths
    finally:
        shutil.rmtree(d, ignore_errors=True)


@contextlib.contextmanager
def clean_env():
    """按 ENV-5 现建一个干净解释器（临时目录里新建、不在库里留）；用完删掉。

    建出来的解释器路径按平台取：Windows 在 `Scripts/` 下，别的在 `bin/` 下。
    """
    d = Path(tempfile.mkdtemp(prefix="tc-venv-"))
    venv = d / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)],
                   check=True, capture_output=True)
    exe = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    try:
        yield exe
    finally:
        shutil.rmtree(d, ignore_errors=True)


def can_import_engine(python):
    return subprocess.run([str(python), "-c", "import tokenizers"],
                          capture_output=True).returncode == 0


def engine_version(python):
    """解释器里那份引擎的版本号；导不进引擎时返回一句空。"""
    p = subprocess.run(
        [str(python), "-c", "import tokenizers;print(tokenizers.__version__)"],
        capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else ""


def source_record(python):
    """解释器里那份引擎的来源记录（direct_url.json）的正文；没有这份记录时返回 None。

    装本地那份包时 pip 会写下这份记录（指向那个文件）；从包索引装的没有它。
    """
    p = subprocess.run(
        [str(python), "-c", "import sysconfig;print(sysconfig.get_paths()['purelib'])"],
        capture_output=True, text=True)
    if p.returncode != 0:
        return None
    hits = sorted(Path(p.stdout.strip()).glob("tokenizers-*.dist-info/direct_url.json"))
    return hits[0].read_text(encoding="utf-8") if hits else None


def happy(rc, out, tokens, chars):
    """TC-1 至 TC-9、TC-13 至 TC-18、TC-22 至 TC-25 那一类：两行输出各对上。"""
    problems = []
    if rc != 0:
        problems.append("退出码 %s，期望 0" % rc)
    lines = out.splitlines()
    want = ["tokens: %d" % tokens, "chars: %d" % chars]
    if lines[:2] != want:
        problems.append("标准输出前两行是 %r，期望 %r" % (lines[:2], want))
    if len(lines) > 2:
        problems.append("标准输出多于两行：%r" % lines[2:])
    return problems


def expect_quiet(err):
    """规格写明「标准错误为空」的那几条：不该有任何安装动作或别的动静。"""
    return [] if not err.strip() else ["标准错误该是空的，实际是 %r" % err.strip()[:200]]


def wind_down(rc, out):
    """TC-10 至 TC-12、TC-19 至 TC-21 那一类：退出码非 0，标准输出一个字符都没有。"""
    problems = []
    if rc == 0:
        problems.append("退出码是 0，期望非 0")
    if out:
        problems.append("标准输出该一个字符都没有，实际是 %r" % out[:200])
    return problems


def last_meaningful_line(text):
    lines = [line for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def mentions_path(text, path):
    """报错里点名某个路径没有：命令行里带的原样出现，回溯里那份是转义过的写法。"""
    return str(path) in text or str(path).replace("\\", "\\\\") in text


# ── TP-1 计数的三道输入与文本取值（TC-1 至 TC-21）──


def test_TC_1_text_option_chinese():
    """TC-1：`--text` 这条道数纯中文，按规范语义加载词表、报出两行。

    覆盖 TCOV-1、TCOV-10、TCOV-19、TCOV-20、TCOV-21、TCOV-38。
    """
    rc, out, err = run_script(["--text", TEXT_CJK])
    return happy(rc, out, 3, 5) + expect_quiet(err)


def test_TC_2_file_route_ascii():
    """TC-2：文件这条道数纯 ASCII，收尾换行也算进字符数。覆盖 TCOV-2、TCOV-9。"""
    with samples_dir() as s:
        rc, out, err = run_script([str(s["DATA-1"])])
    return happy(rc, out, 3, 12) + expect_quiet(err)


def test_TC_3_stdin_route_mixed():
    """TC-3：标准输入这条道，混排文本数得对。覆盖 TCOV-3、TCOV-11。"""
    rc, out, _ = run_script([], stdin=SAMPLES["DATA-12"][1])
    return happy(rc, out, 5, 12)


def test_TC_4_empty_text_counts_zero():
    """TC-4：空文本数出两个 0（甲下边界）。覆盖 TCOV-12、TCOV-29。"""
    rc, out, err = run_script(["--text", ""])
    return happy(rc, out, 0, 0) + expect_quiet(err)


def test_TC_5_one_ascii_char():
    """TC-5：1 个字符（甲下边界上方邻值）、占 1 个字节（乙下边界）。

    覆盖 TCOV-30、TCOV-32。
    """
    rc, out, _ = run_script(["--text", CHAR_A])
    return happy(rc, out, 1, 1)


def test_TC_6_one_two_byte_char():
    """TC-6：一个字符占 2 个字节。覆盖 TCOV-33。"""
    rc, out, _ = run_script(["--text", CHAR_E_ACUTE])
    return happy(rc, out, 1, 1)


def test_TC_7_one_three_byte_char():
    """TC-7：一个字符占 3 个字节。覆盖 TCOV-34。"""
    rc, out, _ = run_script(["--text", CHAR_CJK])
    return happy(rc, out, 1, 1)


def test_TC_8_one_four_byte_char():
    """TC-8：一个字符占 4 个字节（乙上边界）——编成了两个 token。覆盖 TCOV-35。"""
    rc, out, _ = run_script(["--text", CHAR_EMOJI])
    return happy(rc, out, 2, 1)


def test_TC_9_complete_bom_stripped():
    """TC-9：文件开头完整的字节顺序标记（丙上边界）被剥掉。覆盖 TCOV-13、TCOV-41。"""
    with samples_dir() as s:
        rc, out, _ = run_script([str(s["DATA-3"])])
    return happy(rc, out, 1, 2)


def _not_utf8_file(data_id):
    """TC-10 至 TC-12 共用的骨架：解不了码的那几个样本，报错要指认这个路径。"""
    with samples_dir() as s:
        path = s[data_id]
        rc, out, err = run_script([str(path)])
    problems = wind_down(rc, out)
    if ("not valid UTF-8: " + str(path)) not in err:
        problems.append("报错里没指认这个样本：%r" % err.strip()[:200])
    return problems


def test_TC_10_truncated_one_bom_byte():
    """TC-10：开头 1 个字节的残缺形态（丙区间中）以非零退出码收场。

    覆盖 TCOV-6、TCOV-39。
    """
    return _not_utf8_file("DATA-4")


def test_TC_11_truncated_two_bom_bytes():
    """TC-11：开头 2 个字节的残缺形态（丙区间中）以非零退出码收场。

    覆盖 TCOV-6、TCOV-40。
    """
    return _not_utf8_file("DATA-5")


def test_TC_12_surrogate_bytes_rejected():
    """TC-12：形状合法但语义非法的字节序列（代理区编码）同样被拒。覆盖 TCOV-7。"""
    return _not_utf8_file("DATA-6")


def test_TC_13_bom_char_kept_in_option():
    """TC-13：`--text` 开头那个标记字符不被剥、照常计数。覆盖 TCOV-14。"""
    rc, out, _ = run_script(["--text", BOM_CHAR_TEXT])
    return happy(rc, out, 2, 3)


def test_TC_14_special_token_counted():
    """TC-14：特殊 token 的字面形按词表计入，整串算一个 token。覆盖 TCOV-15。"""
    rc, out, _ = run_script(["--text", SPECIAL_TOKEN_TEXT])
    return happy(rc, out, 1, 19)


def test_TC_15_control_chars_in_file():
    """TC-15：控制字符照常计数（NUL 进不了命令行，走文件道）。覆盖 TCOV-16。"""
    with samples_dir() as s:
        rc, out, _ = run_script([str(s["DATA-7"])])
    return happy(rc, out, 3, 3)


def test_TC_16_zero_width_in_option():
    """TC-16：零宽字符照常计数。覆盖 TCOV-17。"""
    rc, out, _ = run_script(["--text", ZERO_WIDTH_TEXT])
    return happy(rc, out, 3, 3)


def test_TC_17_replacement_and_noncharacter_file():
    """TC-17：替换字符与非字符码点照常计数。覆盖 TCOV-18。"""
    with samples_dir() as s:
        rc, out, _ = run_script([str(s["DATA-13"])])
    return happy(rc, out, 3, 2)


def test_TC_18_option_beats_file():
    """TC-18：`--text` 与文件路径同时给时数的是 `--text` 那份——**依据未规定这一处**。

    覆盖 TCOV-8。这一条记的是实现当下的行为，报给用户定口径；实现改了这一条要重判。
    """
    with samples_dir() as s:
        rc, out, _ = run_script([str(s["DATA-2"]), "--text", "hello"])
    return happy(rc, out, 1, 5)


def test_TC_19_missing_path_wind_down():
    """TC-19：路径不存在时怎么收场——报错回溯，末行点名 FileNotFoundError 与那个路径。

    覆盖 TCOV-4、TCOV-27。依据未规定这一处——记的是实现当下的收场方式。
    """
    with samples_dir() as s:
        missing = s["DATA-2"].parent / "not_here.bin"   # 这个位置确认没有这个文件
        rc, out, err = run_script([str(missing)])
    problems = wind_down(rc, out)
    last = last_meaningful_line(err)
    if "FileNotFoundError" not in last or not mentions_path(last, missing):
        problems.append("末行没点名 FileNotFoundError 与那个路径：%r" % last[:200])
    return problems


def test_TC_20_directory_path_wind_down():
    """TC-20：路径是目录时怎么收场——末行点名 Errno 13 的 PermissionError 与那个路径。

    覆盖 TCOV-5、TCOV-27。依据未规定这一处——记的是实现当下的收场方式。
    """
    with samples_dir() as s:
        d = s["DATA-2"].parent
        rc, out, err = run_script([str(d)])
    problems = wind_down(rc, out)
    last = last_meaningful_line(err)
    if ("Errno 13" not in last or "PermissionError" not in last
            or not mentions_path(last, d)):
        problems.append("末行没点名 Errno 13 的 PermissionError 与那个路径：%r" % last[:200])
    return problems


def test_TC_21_two_files_wind_down():
    """TC-21：给了两个文件时怎么收场——命令行用法提示，退出码 2。

    覆盖 TCOV-27。依据未规定这一处——记的是实现当下的收场方式。
    """
    with samples_dir() as s:
        second = s["DATA-2"]
        rc, out, err = run_script([str(s["DATA-1"]), str(second)])
    problems = []
    if rc != 2:
        problems.append("退出码 %s，期望 2" % rc)
    if out:
        problems.append("标准输出该一个字符都没有，实际是 %r" % out[:200])
    if "unrecognized arguments" not in err or str(second) not in err:
        problems.append("用法提示里没提 unrecognized arguments 或第二个路径：%r"
                        % err.strip()[:200])
    return problems


# ── TP-2 首次运行的安装道（TC-22 至 TC-25）──


def test_TC_22_no_install_when_engine_present():
    """TC-22：规则 1——引擎已在位时一个字节都不装。覆盖 TCOV-43。

    标准错误为空即「没有任何安装动作的痕迹」。
    """
    if not can_import_engine(sys.executable):
        return ["ENV-4 的前提不成立：本机解释器里导入不了引擎"]
    rc, out, err = run_script(["--text", TEXT_TWO_CJK])
    return happy(rc, out, 1, 2) + expect_quiet(err)


def test_TC_23_first_run_installs_bundled_wheel():
    """TC-23：规则 2——干净机器上首次运行装的是随技能打包的那份（离线）。

    覆盖 TCOV-44。跑完看两处：装上的版本号是钉住的 0.22.2；pip 写下的来源记录
    指向技能副本 wheels/ 里那份包文件（本地路径），不是包索引。
    """
    if WHEEL is None:
        return ["ENV-3 的前提不成立：技能副本 wheels/ 里那份包不在"]
    with samples_dir() as s:
        with clean_env() as exe:
            if can_import_engine(exe):
                return ["ENV-5 的前提不成立：新建的干净解释器里能导入引擎"]
            rc, out, _ = run_script([str(s["DATA-1"])], python=exe)
            problems = happy(rc, out, 3, 12)
            version = engine_version(exe)
            if version != PINNED:
                problems.append("装上的引擎版本是 %r，期望 %s" % (version, PINNED))
            record = source_record(exe)
            if record is None:
                problems.append("没写下来源记录：看起来不是从本地那份包装的")
            elif WHEEL.name not in record or "file://" not in record:
                problems.append("来源记录没指向技能副本 wheels/ 里那份包：%r" % record[:200])
    return problems


def _copy_with_wheels(replace_broken=False, drop_bundle=False):
    """把 ENV-3 的技能副本整个复制到临时目录，按需改副本的 wheels/；返回（临时目录, 副本）。

    ENV-6（包索引可达）由跑的人先保证——这里不另探一次网，探一次等于多下一份包。
    """
    staging = Path(tempfile.mkdtemp(prefix="tc-skill-copy-"))
    copy = staging / "skill-copy"
    shutil.copytree(SKILL, copy)
    if replace_broken:
        (copy / "wheels" / WHEEL.name).write_bytes(b"")   # 同名的坏文件
    if drop_bundle:
        shutil.rmtree(copy / "wheels")
    return staging, copy


def _online_route_problems(staging, copy):
    """TC-24 与 TC-25 共用的骨架：跑副本里的脚本，版本对得上、来源记录是空的。"""
    try:
        script = copy / "scripts" / "count_tokens.py"
        with clean_env() as exe:
            if can_import_engine(exe):
                return ["ENV-5 的前提不成立：新建的干净解释器里能导入引擎"]
            rc, out, _ = run_script(["--text", TEXT_TWO_CJK], python=exe, script=script)
            problems = happy(rc, out, 1, 2)
            version = engine_version(exe)
            if version != PINNED:
                problems.append("装上的引擎版本是 %r，期望 %s" % (version, PINNED))
            record = source_record(exe)
            if record is not None:
                problems.append("来源记录该是空的（从包索引取的），实际有：%r"
                                % record[:200])
        return problems
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def test_TC_24_broken_wheel_falls_back_online():
    """TC-24：规则 3——打包那份在、可它装不上时，改走联网那条道装 0.22.2。

    覆盖 TCOV-45。副本里那份包换成同名的坏文件（空文件）；来源记录为空说明装的
    不是本地那份，而是从包索引取的。
    """
    if WHEEL is None:
        return ["ENV-3 的前提不成立：技能副本 wheels/ 里那份包不在"]
    staging, copy = _copy_with_wheels(replace_broken=True)
    return _online_route_problems(staging, copy)


def test_TC_25_no_bundle_goes_online():
    """TC-25：规则 4——打包那份压根不在时，直接走联网那条道装 0.22.2。

    覆盖 TCOV-46。副本里 wheels/ 整个目录删掉；来源记录为空说明直接从包索引取的。
    """
    staging, copy = _copy_with_wheels(drop_bundle=True)
    return _online_route_problems(staging, copy)


# 编号由字符串写，函数名里那两个下划线换不掉（`TC_1` 在 Python 里才合法）；
# 落成约定要的就是「照抄编号，连字符换下划线」，这一层对照关系写在这儿：
CASES = [
    ("TC-1", test_TC_1_text_option_chinese),
    ("TC-2", test_TC_2_file_route_ascii),
    ("TC-3", test_TC_3_stdin_route_mixed),
    ("TC-4", test_TC_4_empty_text_counts_zero),
    ("TC-5", test_TC_5_one_ascii_char),
    ("TC-6", test_TC_6_one_two_byte_char),
    ("TC-7", test_TC_7_one_three_byte_char),
    ("TC-8", test_TC_8_one_four_byte_char),
    ("TC-9", test_TC_9_complete_bom_stripped),
    ("TC-10", test_TC_10_truncated_one_bom_byte),
    ("TC-11", test_TC_11_truncated_two_bom_bytes),
    ("TC-12", test_TC_12_surrogate_bytes_rejected),
    ("TC-13", test_TC_13_bom_char_kept_in_option),
    ("TC-14", test_TC_14_special_token_counted),
    ("TC-15", test_TC_15_control_chars_in_file),
    ("TC-16", test_TC_16_zero_width_in_option),
    ("TC-17", test_TC_17_replacement_and_noncharacter_file),
    ("TC-18", test_TC_18_option_beats_file),
    ("TC-19", test_TC_19_missing_path_wind_down),
    ("TC-20", test_TC_20_directory_path_wind_down),
    ("TC-21", test_TC_21_two_files_wind_down),
    ("TC-22", test_TC_22_no_install_when_engine_present),
    ("TC-23", test_TC_23_first_run_installs_bundled_wheel),
    ("TC-24", test_TC_24_broken_wheel_falls_back_online),
    ("TC-25", test_TC_25_no_bundle_goes_online),
]


def main():
    print("跑 %d 条用例（TP-1、TP-2；批一）\n" % len(CASES))
    bad = 0
    for tc, fn in CASES:
        try:
            problems = fn()
        except Exception as exc:  # noqa: BLE001
            problems = ["测试自己崩了：%r" % (exc,)]
        if problems:
            bad += 1
            print("[失败] %s %s" % (tc, fn.__doc__.strip().splitlines()[0].split("：", 1)[-1]))
            for p in problems:
                print("       %s" % p)
        else:
            print("[通过] %s" % tc)
    print()
    if bad:
        print("%d 条没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
