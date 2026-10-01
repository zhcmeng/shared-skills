#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""count_tokens.py 的测试：照 evals/token-counter/test-case-design/ 那几份规格落成。

    python tests/token-counter/test_count_tokens.py

**这是批一**——测试规程规格说明「各批落到哪」那一节里，TP-1 与 TP-2 两条规程的
判据落在命令、标准输出、退出码与盘上的文件上，跑一遍就有结论，落成能跑的测试代码
（TP-3 那九条要读一轮技能被调用时的表现，归批二，落成评测用例，不在这一份里）。

覆盖的编号（按「落成约定」照抄，连字符在代码里写成下划线）：

  - TP-1 脚本层常规路径：TC-1 至 TC-19
  - TP-2 引擎获取路径：TC-20 至 TC-23
  - 覆盖项 TCOV-1 至 TCOV-27
  - 四个模型里这三个落在这一批：TM-1（等价类划分的模型）、TM-2（边界值分析的模型）、
    TM-3（判定表测试的模型）；TM-4 是场景测试的模型，它那九条用例归批二，不在这里
  - 数据项 DATA-1 至 DATA-15
  - 环境项 ENV-1、ENV-2、ENV-3、ENV-4、ENV-5、ENV-6、ENV-7、ENV-8

**期望值一律照规格抄，不照脚本现在的输出抄。**这一份是拿规格判被测对象：脚本吐出来
的数与规格对不上，要报出来，不能反过来把规格改成脚本的样子——那这个测试就白写了。

**TC-18 是记录型的一条**：规格写明「依据未规定这一处」，它记的是实现当下的行为，
不是一条判对错的判据；实现改了这一条要重判（见那一条自己的说明）。

**TC-22 与 TC-23 会动盘**：TC-22 要往 `wheels/` 里放一个假 wheel、把真的挪出去，
跑完恢复原样（finally 里恢复，恢复完再核一遍）；TC-23 那一处的「断网」是把 pip 的
索引地址指到黑洞上近似的，不是真把网卡断掉——理由写在那一处。
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

# 本机实测：随技能打包的那个 wheel。TC-21 与 TC-22 要拿它的名字比版本、造假的。
WHEEL = next(iter(WHEELS.glob("*.whl")), None)

BOM = b"\xef\xbb\xbf"

# DATA-1 至 DATA-5：五段文字，正文照测试数据需求那份取
TEXT_A = "a"                          # DATA-1
TEXT_CJK = "你好，世界"                # DATA-2
TEXT_EMOJI = "😀"                     # DATA-3
TEXT_SPACES = "   "                   # DATA-4，三个半角空格 U+0020
TEXT_SPECIAL = "<｜end▁of▁sentence｜>"  # DATA-5

# DATA-6 至 DATA-12：七个样本文件，字节照描述栏写明的造；文件名跟着编号走
SAMPLES = {
    "DATA-6": TEXT_CJK.encode("utf-8"),        # 15 字节，不带标记
    "DATA-7": BOM + TEXT_CJK.encode("utf-8"),  # 18 字节，带标记
    "DATA-8": b"",                             # 0 字节
    "DATA-9": b"a",                            # 1 字节
    "DATA-10": BOM,                            # 3 字节，只有标记
    "DATA-11": BOM + b"a",                     # 4 字节，标记加一个字符
    "DATA-12": "你好".encode("gbk"),            # C4 E3 BA C3，按 UTF-8 解不开
}


def run_script(args=(), stdin=b"", python=None, env=None):
    """跑被测脚本，返回（退出码, 标准输出, 标准错误）。"""
    proc = subprocess.run(
        [python or sys.executable, str(SCRIPT), *args],
        input=stdin, capture_output=True, env=env)
    return (proc.returncode,
            proc.stdout.decode("utf-8", "replace"),
            proc.stderr.decode("utf-8", "replace"))


@contextlib.contextmanager
def samples_dir():
    """按 TP-1 的「启动」把七个样本摆在同一个临时目录里；跑完清掉。"""
    d = Path(tempfile.mkdtemp(prefix="tc-samples-"))
    try:
        paths = {}
        for name, data in SAMPLES.items():
            p = d / (name + ".txt")
            p.write_bytes(data)
            paths[name] = p
        yield paths
    finally:
        shutil.rmtree(d, ignore_errors=True)


@contextlib.contextmanager
def clean_env():
    """按 ENV-5 现建一个干净环境，里面没有装引擎；用完删掉。

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


def engine_fingerprint(python):
    """引擎的版本号与安装位置；导不进引擎时返回一句空。"""
    p = subprocess.run(
        [str(python), "-c",
         "import tokenizers;print(tokenizers.__version__);print(tokenizers.__file__)"],
        capture_output=True)
    return p.stdout.decode("utf-8", "replace").strip() if p.returncode == 0 else ""


def can_import_engine(python):
    return subprocess.run([str(python), "-c", "import tokenizers"],
                          capture_output=True).returncode == 0


def happy(rc, out, tokens, chars):
    """TC-1 至 TC-14 那一类：退出码 0，标准输出正好两行，`tokens:` 与 `chars:` 各一行。"""
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


def no_count_line(rc, out):
    """TC-15 至 TC-19 那一类：标准输出上没有 `tokens:` 那一行，退出码非 0。"""
    problems = []
    if rc == 0:
        problems.append("退出码是 0，期望非 0")
    if any(line.startswith("tokens:") for line in out.splitlines()):
        problems.append("标准输出上不该有 `tokens:` 那一行，实际是 %r" % out)
    return problems


# ── TP-1 脚本层常规路径（TC-1 至 TC-19，判据落在命令、标准输出与退出码上）──


def test_TC_1_text_single_ascii_char():
    """TC-1：`--text` 给出一个 ASCII 字符。覆盖 TCOV-1、TCOV-11、TCOV-17、TCOV-20。"""
    rc, out, _ = run_script(["--text", TEXT_A])          # DATA-1
    return happy(rc, out, 1, 1)


def test_TC_2_text_cjk_counts_exactly():
    """TC-2：一段中文，并钉住 `chars` 数的是字符数不是字节数（5 个字符、15 个字节）。

    覆盖 TCOV-12、TCOV-17。
    """
    rc, out, _ = run_script(["--text", TEXT_CJK])        # DATA-2
    return happy(rc, out, 3, 5)


def test_TC_3_text_astral_emoji():
    """TC-3：基本平面之外的字符。覆盖 TCOV-13、TCOV-17。"""
    rc, out, _ = run_script(["--text", TEXT_EMOJI])      # DATA-3
    return happy(rc, out, 2, 1)


def test_TC_4_text_whitespace_only():
    """TC-4：只由空白字符组成的文本。覆盖 TCOV-15、TCOV-17。"""
    rc, out, _ = run_script(["--text", TEXT_SPACES])     # DATA-4
    return happy(rc, out, 1, 3)


def test_TC_5_text_special_token_literal():
    """TC-5：特殊 token 的字面量按官方词表计入，被当作一个 token。

    规格只钉了第一行 `tokens: 1`，`chars` 那一行没写，所以只判第一行。
    覆盖 TCOV-14、TCOV-17。
    """
    rc, out, _ = run_script(["--text", TEXT_SPECIAL])    # DATA-5
    problems = []
    if rc != 0:
        problems.append("退出码 %s，期望 0" % rc)
    if out.splitlines()[:1] != ["tokens: 1"]:
        problems.append("标准输出第一行是 %r，期望 `tokens: 1`" % out.splitlines()[:1])
    return problems


def test_TC_6_text_empty_string():
    """TC-6：`--text` 给了但内容是零字符。覆盖 TCOV-16、TCOV-17、TCOV-19。"""
    rc, out, _ = run_script(["--text", ""])
    return happy(rc, out, 0, 0)


def test_TC_7_file_plain_utf8():
    """TC-7：由文件路径给出文本，文件是不带标记的 UTF-8。

    覆盖 TCOV-2、TCOV-8、TCOV-17。
    """
    with samples_dir() as s:
        rc, out, _ = run_script([str(s["DATA-6"])])
    return happy(rc, out, 3, 5)


def test_TC_8_file_utf8_with_bom():
    """TC-8：带标记的文件被正常读取，标记不算进正文——与 TC-7 同值即说明这一点。

    覆盖 TCOV-9、TCOV-17。
    """
    with samples_dir() as s:
        rc, out, _ = run_script([str(s["DATA-7"])])
    return happy(rc, out, 3, 5)


def test_TC_9_file_zero_bytes():
    """TC-9：零字节文件这条边界。覆盖 TCOV-17、TCOV-21。"""
    with samples_dir() as s:
        rc, out, _ = run_script([str(s["DATA-8"])])
    return happy(rc, out, 0, 0)


def test_TC_10_file_one_byte():
    """TC-10：单字节文件这条边界。覆盖 TCOV-17、TCOV-22。"""
    with samples_dir() as s:
        rc, out, _ = run_script([str(s["DATA-9"])])
    return happy(rc, out, 1, 1)


def test_TC_11_file_bom_only():
    """TC-11：整个文件只有那三个标记字节。覆盖 TCOV-17、TCOV-23。"""
    with samples_dir() as s:
        rc, out, _ = run_script([str(s["DATA-10"])])
    return happy(rc, out, 0, 0)


def test_TC_12_file_bom_plus_one_char():
    """TC-12：标记之后只有一个字符这条边界。覆盖 TCOV-17、TCOV-24。"""
    with samples_dir() as s:
        rc, out, _ = run_script([str(s["DATA-11"])])
    return happy(rc, out, 1, 1)


def test_TC_13_stdin_pipe_cjk():
    """TC-13：由标准输入给出文本。覆盖 TCOV-3、TCOV-12、TCOV-17。"""
    rc, out, _ = run_script([], stdin=SAMPLES["DATA-6"])
    return happy(rc, out, 3, 5)


def test_TC_14_no_source_at_all():
    """TC-14：三种来路都不给、标准输入也为空——依据没把它定成错误，按空文本处理。

    覆盖 TCOV-4、TCOV-17。
    """
    rc, out, _ = run_script([], stdin=b"")
    return happy(rc, out, 0, 0)


def test_TC_15_file_path_missing():
    """TC-15：文件路径不存在。覆盖 TCOV-5、TCOV-18。"""
    with samples_dir() as s:
        missing = s["DATA-6"].parent / "盘上不存在-8f3a.txt"   # DATA-13
        rc, out, _ = run_script([str(missing)])
    return no_count_line(rc, out)


def test_TC_16_file_path_is_directory():
    """TC-16：文件路径指向一个目录（DATA-14 取技能目录本身）。覆盖 TCOV-6、TCOV-18。"""
    rc, out, _ = run_script([str(SKILL)])
    return no_count_line(rc, out)


def test_TC_17_input_file_not_utf8():
    """TC-17：文件不是 UTF-8 时报错，且报错里指认是哪个输入。

    覆盖 TCOV-10、TCOV-18。
    """
    with samples_dir() as s:
        path = s["DATA-12"]
        rc, out, err = run_script([str(path)])
    problems = no_count_line(rc, out)
    # 规格说的是「报错信息里出现」，没钉哪一路，两路合起来找
    if ("not valid UTF-8: " + str(path)) not in (out + err):
        problems.append("报错里没指认这个样本文件的路径：%r" % (out + err).strip()[:200])
    return problems


def test_TC_18_text_arg_beats_file():
    """TC-18：`--text` 与文件路径同时给出时听谁的——**依据未规定这一处**。

    规格写明「依据推不出预期结果」，所以这一条不判对错，只把实现当下的行为记下来：
    `--text` 胜出、文件被静默忽略，两行输出与只给 `--text "a"` 时一样，没有任何提示
    说文件被忽略了。实现改了这一条要重判——这正是规格里那句「依据补齐后这一条要重判」
    的意思。覆盖 TCOV-7。
    """
    with samples_dir() as s:
        rc, out, err = run_script([str(s["DATA-6"]), "--text", TEXT_A])
    problems = happy(rc, out, 1, 1)
    if err.strip():
        problems.append("记录的行为是「文件被静默忽略」，标准错误却有话：%r" % err.strip()[:200])
    return problems


def test_TC_19_input_stdin_not_utf8():
    """TC-19：标准输入不是 UTF-8 时报错，报错里指认的是标准输入而不是文件路径。

    与 TC-17 是同一覆盖项的另一条失败路子。覆盖 TCOV-10、TCOV-18。
    """
    rc, out, err = run_script([], stdin=SAMPLES["DATA-12"])
    problems = no_count_line(rc, out)
    if "not valid UTF-8: <stdin>" not in (out + err):
        problems.append("报错里没指认标准输入：%r" % (out + err).strip()[:200])
    return problems


# ── TP-2 引擎获取路径（TC-20 至 TC-23，判据还要看盘上装没装上引擎）──


def test_TC_20_engine_already_present():
    """TC-20：判定规则 1——引擎已可导入时不做任何安装（ENV-4、TM-3 的规则 1）。

    覆盖 TCOV-25。跑前跑后各取一次引擎的版本号与安装位置，两边要一模一样。
    """
    before = engine_fingerprint(sys.executable)
    if not before:
        return ["ENV-4 的前提不成立：本机这个解释器里导入不了引擎"]
    rc, out, err = run_script(["--text", TEXT_A])
    problems = happy(rc, out, 1, 1)
    if "Installing" in err:
        problems.append("已装好的时候不该有安装动作，标准错误里却有：%r" % err.strip()[:200])
    after = engine_fingerprint(sys.executable)
    if after != before:
        problems.append("跑完之后引擎的版本号或安装位置变了：%r → %r" % (before, after))
    return problems


def test_TC_21_clean_env_installs_bundled_wheel():
    """TC-21：判定规则 2——引擎不可导入、打包 wheel 可用时，离线装上那个 wheel。

    覆盖 TCOV-26。装上的版本要与 `wheels/` 里那个 wheel 同名同版本。
    """
    if WHEEL is None:
        return ["ENV-7 的前提不成立：wheels/ 里一个 wheel 都没有"]
    want = WHEEL.name.split("-")[1]
    with clean_env() as exe:
        if can_import_engine(exe):
            return ["ENV-5 的前提不成立：新建的干净环境里能导入引擎"]
        rc, out, err = run_script(["--text", TEXT_A], python=exe)
        problems = happy(rc, out, 1, 1)
        got = engine_fingerprint(exe)
        if not got:
            problems.append("跑完之后干净环境里还是导入不了引擎；标准错误：%r" % err.strip()[:200])
        elif want not in got:
            problems.append("装上的版本与 wheels/ 里那个 wheel 对不上：期望 %s，实际 %r" % (want, got))
    return problems


def test_TC_22_incompatible_wheel_falls_back_to_network():
    """TC-22：判定规则 3——打包 wheel 不可用时回落到联网安装写死版本（ENV-6）。

    三步：把 DATA-15 那个假 wheel 放进 `wheels/`、真的挪出去；跑；把 `wheels/`
    恢复原样。恢复放在 finally 里，恢复完再核一遍盘上是不是原来那一个——这一条
    会动测试项自己的目录，恢复不了要立刻知道。覆盖 TCOV-27。
    """
    if WHEEL is None:
        return ["ENV-7 的前提不成立：wheels/ 里一个 wheel 都没有"]
    # DATA-15：与真 wheel 同名同版本，只把平台标记那段换掉；内容空文件即可
    parts = WHEEL.name[:-len(".whl")].split("-")
    parts[-1] = "manylinux_2_17_x86_64"
    fake = WHEELS / ("-".join(parts) + ".whl")
    stash_dir = Path(tempfile.mkdtemp(prefix="tc-wheel-stash-"))
    stash = stash_dir / WHEEL.name
    problems = []
    try:
        shutil.move(str(WHEEL), str(stash))
        fake.write_bytes(b"")
        with clean_env() as exe:
            if can_import_engine(exe):
                return ["ENV-5 的前提不成立：新建的干净环境里能导入引擎"]
            rc, out, err = run_script(["--text", TEXT_A], python=exe)
            problems += happy(rc, out, 1, 1)
            if "from PyPI" not in err:
                problems.append("没看到回落到联网那一路（标准错误里没有 `from PyPI`）：%r"
                                % err.strip()[:200])
            if not engine_fingerprint(exe):
                problems.append("跑完之后干净环境里还是导入不了引擎；标准错误：%r"
                                % err.strip()[:200])
    finally:
        # 第三步：按 DATA-15 的重置需求把 wheels/ 恢复原样
        if fake.exists():
            fake.unlink()
        if stash.exists():
            shutil.move(str(stash), str(WHEEL))
        shutil.rmtree(stash_dir, ignore_errors=True)
    left = sorted(p.name for p in WHEELS.glob("*.whl"))
    if left != [WHEEL.name]:
        problems.append("跑完之后 wheels/ 没恢复原样：%r" % left)
    return problems


def test_TC_23_clean_env_offline_install():
    """TC-23：判定规则 2 的离线性质——同一覆盖项的另一条检查：断网也装得成。

    覆盖 TCOV-26。

    **「断网」是近似的**：真把网卡断掉要动系统设置，测试里做不了，所以改成把 pip
    的索引地址指到一个黑洞端口上、超时压到 1 秒、不许重试——脚本要是走了联网那一路，
    这一步必然失败；装成了就说明走的是随技能打包的 wheel。再钉一句 `(offline)`：
    那是离线那一路的开场白，比「装成了」更直接地说明走的是哪一条。
    """
    env = dict(os.environ)
    env.update({
        "PIP_INDEX_URL": "http://127.0.0.1:9/simple",
        "PIP_TIMEOUT": "1",
        "PIP_RETRIES": "0",
        "PIP_NO_INPUT": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    })
    with clean_env() as exe:
        if can_import_engine(exe):
            return ["ENV-5 的前提不成立：新建的干净环境里能导入引擎"]
        rc, out, err = run_script(["--text", TEXT_A], python=exe, env=env)
        problems = happy(rc, out, 1, 1)
        if "(offline)" not in err:
            problems.append("没走离线那一路（标准错误里没有 `(offline)`）：%r" % err.strip()[:200])
        if not engine_fingerprint(exe):
            problems.append("断着网跑完之后干净环境里导入不了引擎；标准错误：%r" % err.strip()[:200])
    return problems


# 编号由字符串写，函数名里那两个下划线换不掉（`TC_1` 在 Python 里才合法）；
# 落成约定要的就是「照抄编号，连字符换下划线」，这一层对照关系写在这儿：
CASES = [
    ("TC-1", test_TC_1_text_single_ascii_char),
    ("TC-2", test_TC_2_text_cjk_counts_exactly),
    ("TC-3", test_TC_3_text_astral_emoji),
    ("TC-4", test_TC_4_text_whitespace_only),
    ("TC-5", test_TC_5_text_special_token_literal),
    ("TC-6", test_TC_6_text_empty_string),
    ("TC-7", test_TC_7_file_plain_utf8),
    ("TC-8", test_TC_8_file_utf8_with_bom),
    ("TC-9", test_TC_9_file_zero_bytes),
    ("TC-10", test_TC_10_file_one_byte),
    ("TC-11", test_TC_11_file_bom_only),
    ("TC-12", test_TC_12_file_bom_plus_one_char),
    ("TC-13", test_TC_13_stdin_pipe_cjk),
    ("TC-14", test_TC_14_no_source_at_all),
    ("TC-15", test_TC_15_file_path_missing),
    ("TC-16", test_TC_16_file_path_is_directory),
    ("TC-17", test_TC_17_input_file_not_utf8),
    ("TC-18", test_TC_18_text_arg_beats_file),
    ("TC-19", test_TC_19_input_stdin_not_utf8),
    ("TC-20", test_TC_20_engine_already_present),
    ("TC-21", test_TC_21_clean_env_installs_bundled_wheel),
    ("TC-22", test_TC_22_incompatible_wheel_falls_back_to_network),
    ("TC-23", test_TC_23_clean_env_offline_install),
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
