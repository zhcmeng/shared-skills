#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DeepSeek official tokenizer exact token counter.

Loads the bundled official tokenizer.json through the tokenizers
Tokenizer.from_file engine, i.e. the tokenizer.json spec semantics. Do NOT
switch to transformers.AutoTokenizer: its legacy-compat path disagrees with
the spec semantics on strings containing spaces or leading CJK (and can even
encode pure-CJK text to an empty list).

The skill is fully self-contained: no preinstalled library needed on the
target machine. Dependency strategy at first run:
  1. tokenizers already importable -> use it
  2. else install the bundled wheel (wheels/*.whl; abi3 -> one wheel serves
     CPython 3.9+ on Windows x64) with --no-deps: the engine never imports
     huggingface_hub when loading from a local file, verified on a clean
     venv without huggingface_hub (2026-09-04)
  3. else (non-Windows / other arch) fall back to a networked
     `pip install tokenizers==0.22.2`

Usage:
    count_tokens.py <file>            # count tokens of a UTF-8 text file
    count_tokens.py --text "..."      # count tokens of a string
    <command> | count_tokens.py       # count tokens from stdin
"""

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
TOKENIZER_FILE = SKILL_ROOT / "tokenizer.json"  # official vocab, bundled
PINNED = "0.22.2"  # engine version used for the networked fallback
WHEEL = next(iter((SKILL_ROOT / "wheels").glob("*.whl")), None)


def ensure_tokenizers() -> None:
    """Make tokenizers importable: already installed, bundled wheel, or PyPI."""
    if importlib.util.find_spec("tokenizers") is not None:
        return
    if WHEEL is not None:
        sys.stderr.write("Installing bundled tokenizers wheel (offline) ...\n")
        ok = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-deps", "-q", str(WHEEL)],
            capture_output=True,
        ).returncode == 0
        if ok:
            return
    sys.stderr.write(f"Installing tokenizers=={PINNED} from PyPI ...\n")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", f"tokenizers=={PINNED}"],
        check=True,
    )


def count_tokens(text: str) -> int:
    ensure_tokenizers()
    from tokenizers import Tokenizer
    return len(Tokenizer.from_file(str(TOKENIZER_FILE)).encode(text).ids)


def read_source(args) -> str:
    if args.text is not None:
        return args.text
    raw = Path(args.file).read_bytes() if args.file else sys.stdin.buffer.read()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise SystemExit(f"not valid UTF-8: {args.file or '<stdin>'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Count DeepSeek tokens exactly (official tokenizer).")
    parser.add_argument("file", nargs="?", help="UTF-8 text file to count")
    parser.add_argument("--text", help="literal text to count")
    args = parser.parse_args()

    text = read_source(args)
    n = count_tokens(text)
    print(f"tokens: {n}")
    print(f"chars: {len(text)}")


if __name__ == "__main__":
    main()
