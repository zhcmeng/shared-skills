#!/usr/bin/env python3
"""Download a web page to Markdown AND localize its images in one step.

Usage:
    python web_download.py <url> -o <out.md>

Steps:
    1. `defuddle parse <url> --markdown -o <out.md>`
    2. localize remote images (markdown + HTML <img>) into <out.md dir>/images/

Requires `defuddle` on PATH (https://github.com/... — the defuddle CLI).
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from download_md_images import localize_files  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description='Download a web page to Markdown and localize its images.')
    parser.add_argument('url', help='Web page URL (http/https)')
    parser.add_argument('-o', '--out', required=True,
                        help='Output Markdown file path')
    parser.add_argument('--no-images', action='store_true',
                        help='Skip image localization (defuddle only)')
    args = parser.parse_args()

    if not args.url.startswith(('http://', 'https://')):
        print('Error: url must start with http:// or https://', file=sys.stderr)
        sys.exit(1)

    out = os.path.abspath(args.out)
    out_dir = os.path.dirname(out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # Step 1: defuddle
    cmd = ['defuddle', 'parse', args.url, '--markdown', '-o', out]
    print(f'[defuddle] {" ".join(cmd)}')
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.isfile(out) or os.path.getsize(out) == 0:
        print('Warning: defuddle returned non-zero or produced empty output.',
              file=sys.stderr)
        if r.stderr:
            print(r.stderr, file=sys.stderr)
        if not os.path.isfile(out):
            print('Abort: no Markdown produced.', file=sys.stderr)
            sys.exit(1)

    # Step 2: localize images
    if args.no_images:
        print('Skipped image localization (--no-images).')
        return
    localize_files([out])


if __name__ == '__main__':
    main()
