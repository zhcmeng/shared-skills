"""pdf-to-md 的体检：这台机器现在能不能转。

**只用标准库，不 import aistudio / convert。** 那三个依赖缺一个转换就跑不
起来，而体检恰恰要在这时候还能跑、并把缺什么说出来——在这儿 import
requests，等于体检和有病的那一方一起躺下。

最后一项不自己重写提交和轮询，而是用子进程跑 convert.py 的**真命令行**：
重写一遍等于验了另一套代码，真命令行哪天坏了，体检照样全绿。
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
CONVERT = os.path.join(HERE, "convert.py")
SAMPLE_PDF = os.path.join(os.path.dirname(HERE), "assets", "doctor-sample.pdf")
SAMPLE_STEM = os.path.splitext(os.path.basename(SAMPLE_PDF))[0]

# 照抄 aistudio.TOKEN_ENV 的一份：那边 import 了 requests，这边不能碰它。
# 抄错了就永远报「没配」，所以测试里有一条专门拿 aistudio 的名字对它。
TOKEN_ENV = "PADDLEOCR_MCP_AISTUDIO_ACCESS_TOKEN"

# 样例正文里那句话。转出来认不出它就说明服务读到的内容不对。
# 改 assets/doctor-sample.html 里那句，就得同步改这里。
SAMPLE_MARKER = "DOCTOR-SAMPLE-8642"

SMOKE_NAME = "真转一份内置 1 页 PDF"
SMOKE_TIMEOUT = 300.0       # 1 页的样例实测十几秒，5 分钟还没完就是卡住了


@dataclass
class Check:
    """一项检查的结果：过没过、一句话说清、不过时怎么修。"""
    name: str
    ok: bool
    detail: str = ""
    fix: str = ""


def _find_uv():
    return shutil.which("uv")


def check_uv():
    if _find_uv():
        return Check("uv 在 PATH 上", True)
    return Check(
        "uv 在 PATH 上", False,
        "找不到 uv 这条命令。转换是 `uv run` 起的，没有它什么都跑不了。",
        "装一个（https://docs.astral.sh/uv/ 上有各系统的装法），"
        "装完重开一个终端让 PATH 生效。")


def check_token():
    raw = os.environ.get(TOKEN_ENV, "")
    if not raw.strip():
        return Check(
            "token 环境变量在", False,
            f"环境里没有 {TOKEN_ENV}。",
            "在 ~/.claude/settings.json 的 env 段里设一次：\n"
            f'  {{"env": {{"{TOKEN_ENV}": "<你的 AI Studio token>"}}}}')
    # 只提醒、不算不通过：服务收不收得下这个带空白的 token 不好说，
    # 让下一项真转一次自己说了算——体检不该替服务下结论。
    note = "（首尾有空白字符，多半是复制时带上的）" if raw != raw.strip() else ""
    return Check("token 环境变量在", True, note)


def _probe_writable(directory):
    """真写一个文件再删掉。

    不看权限位：Windows 上那套判断靠不住，能写才算能写。
    """
    fd, path = tempfile.mkstemp(dir=directory, prefix=".pdf-to-md-体检-")
    os.close(fd)
    os.remove(path)


def _nearest_existing(path):
    """往上找到第一个已经存在的目录；一路找到根都没有就返回 None。"""
    current = os.path.abspath(path)
    while not os.path.exists(current):
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent
    return current


def check_output_dir(path):
    if os.path.isfile(path):
        return Check(
            "输出目录能写", False,
            f"{path} 已经是个文件了，不是目录。",
            "换一个目录，或者把那个文件挪开。")
    where = _nearest_existing(path)
    if where is None:
        return Check(
            "输出目录能写", False,
            f"{path} 往上找不到任何一个已经存在的目录。",
            "路径多半写错了，检查一下盘符和目录名。")
    try:
        _probe_writable(where)
    except OSError as exc:
        return Check(
            "输出目录能写", False,
            f"{where} 写不进去：{exc}",
            "换一个能写的目录。")
    if where == os.path.abspath(path):
        return Check("输出目录能写", True, f"{path} 可以写。")
    # 还没建的输出目录是常态，转换时会自己建。这里探的是最近的上级，
    # 并且不把 path 真建出来——路径写错了的时候，体检不该在盘上留个空目录。
    return Check("输出目录能写", True,
                 f"{path} 还不存在，转换时会自己建；"
                 f"已经确认能建它的 {where} 可以写。")


def smoke_command(out_dir):
    """体检跑的那条命令行，和 SKILL.md 里写着的那条一致。"""
    return ["uv", "run", "--with", "requests", "--with", "lxml", "--with", "tabulate",
            "python", CONVERT, SAMPLE_PDF, "--output", out_dir]


def _run_smoke(cmd, timeout):
    """跑子进程并按 UTF-8 收输出。

    子进程的输出接的是管道、不是控制台，convert.py 那边会自己改成 UTF-8
    （见 convert.prefer_utf8），所以这边按 UTF-8 解。uv 自己在 python 起来
    之前打的报错未必是这个编码——errors="replace" 兜住，别在解码上崩掉，
    那几行是给人看的诊断信息，认得出大意就够。
    """
    return subprocess.run(cmd, capture_output=True, timeout=timeout,
                          text=True, encoding="utf-8", errors="replace")


def _tail(text, limit=6):
    """取末尾几行非空文本。失败原因在末尾，前面全是进度帧。"""
    lines = [line.strip() for line in text.replace("\r", "\n").splitlines()
             if line.strip()]
    return "\n".join(lines[-limit:])


def check_smoke(runner=None):
    """真转一份样例，看盘上落下了什么。

    判据是**产物**，不是退出码：体检要回答的是「能不能转出东西来」。
    """
    runner = _run_smoke if runner is None else runner
    if not os.path.isfile(SAMPLE_PDF):
        return Check(
            SMOKE_NAME, False,
            f"skill 装得不全：样例 PDF 不在 {SAMPLE_PDF}。",
            "把整个 skills/pdf-to-md/ 一起拷过来，光有 scripts/ 不够。")

    with tempfile.TemporaryDirectory(prefix="pdf-to-md-体检-") as tmp:
        out_root = os.path.join(tmp, "out")
        t0 = time.time()
        try:
            proc = runner(smoke_command(out_root), SMOKE_TIMEOUT)
        except subprocess.TimeoutExpired:
            return Check(
                SMOKE_NAME, False,
                f"超时：跑了 {SMOKE_TIMEOUT:.0f} 秒还没回来，已经掐掉。"
                f"样例只有 1 页，正常十几秒就该完。",
                "多半是卡在连不上服务上。换个网络再试；"
                "连不上时真转也一样会这么一直等。")
        elapsed = time.time() - t0

        if proc.returncode != 0:
            words = _tail(proc.stdout) or _tail(proc.stderr) or "（它什么都没输出）"
            return Check(
                SMOKE_NAME, False,
                f"那条命令行退出码 {proc.returncode}。它自己的话：\n" +
                "\n".join("    " + line for line in words.splitlines()),
                "上面是服务或脚本的原话，按它说的处理。")

        md = os.path.join(out_root, SAMPLE_STEM, SAMPLE_STEM + ".md")
        if not os.path.isfile(md):
            return Check(
                SMOKE_NAME, False,
                f"命令行说成功了，但 {SAMPLE_STEM}/"
                f"{SAMPLE_STEM}.md 没落下来。",
                "这是本 skill 自己的毛病，不是环境问题："
                "转换那一步报上去了，盘上却没有产物。")
        with open(md, encoding="utf-8") as f:
            text = f.read()
        if SAMPLE_MARKER not in text:
            return Check(
                SMOKE_NAME, False,
                f"正文落下来了，但里面没有样例那句话（{SAMPLE_MARKER}）——"
                f"服务认出来的内容不对。",
                "换个时间再试一次；还是这样就是服务那边的问题。")
        return Check(SMOKE_NAME, True, f"{elapsed:.1f} 秒，正文里认出了样例的标记")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="doctor.py",
        description="检查这台机器现在能不能用 pdf-to-md 转 PDF")
    parser.add_argument("--output", default=None,
                        help="顺便验一下这个输出目录写不写得进去")
    return parser.parse_args(argv)


def _emit(check, out):
    mark = "通过  " if check.ok else "不通过"
    head = f"  {mark}  {check.name}"
    if check.detail:
        head += f"：{check.detail}"
    for line in head.splitlines():
        out.write(line + "\n")
    for line in check.fix.splitlines():
        out.write(" " * 10 + line + "\n")


def main(argv=None):
    # 和 convert.py 一样：输出被重定向走时按 UTF-8 吐字节，见那边的 prefer_utf8
    prefer_utf8(sys.stdout)
    prefer_utf8(sys.stderr)
    args = parse_args(argv)

    # 前面几项查的都是本机，免费，一次全跑完——把毛病一次说清，别让人
    # 修一个跑一次。最后那项要花配额、要等十几秒，前面全绿了才跑。
    checks = [check_uv(), check_token()]
    if args.output:
        checks.append(check_output_dir(args.output))
    local_ok = all(check.ok for check in checks)
    if local_ok:
        checks.append(check_smoke())

    out = sys.stdout
    out.write("pdf-to-md 体检\n\n")
    for check in checks:
        _emit(check, out)
    if local_ok:
        out.write("\n  （样例转出来的东西落在临时目录里，跑完就删，"
                  "不会进你的输出目录）\n")

    # 结论看的是全部检查，不只是本机那几项——最后一项红着也是转不了。
    if all(check.ok for check in checks):
        out.write("\n这台机器现在能转。\n")
        return 0
    if not local_ok:
        out.write(f"\n  「{SMOKE_NAME}」这项没跑：上面有不通过的地方，"
                  f"跑下去是白花配额。\n")
    out.write("\n这台机器现在转不了，先把上面标「不通过」的处理掉。\n")
    return 2


def prefer_utf8(stream):
    """和 convert.prefer_utf8 同一份逻辑，抄过来的。

    那边 import 了 requests，这边不能 import 它（见本模块开头），所以只能
    抄一份。测试里有一条在真管道上验过：这段抄对了没。
    """
    if stream.isatty():
        return
    if (getattr(stream, "encoding", "") or "").lower().replace("-", "") == "utf8":
        return
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
