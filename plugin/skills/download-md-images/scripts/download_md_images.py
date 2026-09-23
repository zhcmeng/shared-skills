#!/usr/bin/env python3
"""Download remote images referenced in Markdown file(s) and replace URLs with local paths.

Supports both markdown `![alt](https://...)` and HTML `<img src="https://...">`.

Usage:
    python download_md_images.py <file1.md> [file2.md ...]

- Images are saved to `<md所在目录>/images/image_NNN.ext`.
- Files in the SAME directory share a global counter and URL→name map,
  so the same URL across files maps to one local file (no collision / re-download).
- Same URL within a file is downloaded once (dedup).
- Download failure: keep original URL, append `<!-- REMOTE_IMAGE:下载失败 -->`.
- No remote images: normal exit with a notice.
"""

import os
import re
import sys
import urllib.request

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
TIMEOUT = 20

# Matches ![alt](https://url) or ![alt](https://url "title")
IMG_RE = re.compile(
    r'!\[(?P<alt>[^\]]*)\]\((?P<url>https?://[^)\s]+)'
    r'(?:\s+"[^"]*")?\)'
)

# Matches an HTML <img ...> tag (void element; attributes contain no '>')
HTML_IMG_RE = re.compile(r'<img\b[^>]*>', re.IGNORECASE)

ALLOWED_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg'}


def find_remote_images(content):
    """Return list of {alt, url, start, end, full_text} for markdown images."""
    results = []
    for m in IMG_RE.finditer(content):
        results.append({
            'alt': m.group('alt'),
            'url': m.group('url'),
            'start': m.start(),
            'end': m.end(),
            'full_text': m.group(0),
        })
    return results


def find_html_images(content):
    """Return list of {alt, url, start, end, full_text} for HTML <img> tags."""
    results = []
    for m in HTML_IMG_RE.finditer(content):
        tag = m.group(0)
        src_m = re.search(r'src="(https?://[^"]+)"', tag)
        if not src_m:
            continue
        alt_m = re.search(r'alt="([^"]*)"', tag)
        alt = alt_m.group(1) if alt_m else ''
        results.append({
            'alt': alt,
            'url': src_m.group(1),
            'start': m.start(),
            'end': m.end(),
            'full_text': tag,
        })
    return results


def collect_images(content):
    """Return all remote images (markdown + HTML), sorted by position."""
    out = find_remote_images(content) + find_html_images(content)
    out.sort(key=lambda r: r['start'])
    return out


def extract_extension(url):
    """Extract file extension from URL. Defaults to .png for unknown/missing."""
    path = url.split('?')[0]
    ext = os.path.splitext(path)[1].lower()
    if ext in ALLOWED_EXTS:
        return ext
    return '.png'


def build_referer_from_frontmatter(content):
    """Extract source_url from YAML frontmatter to use as HTTP Referer."""
    fm_match = re.match(
        r'---\s*\n.*?^source_url:\s*(https?://\S+).*?\n---',
        content, re.DOTALL | re.MULTILINE
    )
    if fm_match:
        return fm_match.group(1)
    return ''


def _download(url, referer):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Referer': referer or url,
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def _next_counter(img_dir):
    """Return the next image index, after the highest existing image_NNN.* in the dir."""
    if not os.path.isdir(img_dir):
        return 0
    max_n = 0
    for fn in os.listdir(img_dir):
        m = re.match(r'image_(\d{3,})\.', fn)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return max_n


def localize_files(files):
    """Download images for all given files, deduping per directory. Returns download count."""
    groups = {}
    for fp in files:
        if not os.path.isfile(fp):
            print(f'Error: file not found: {fp}', file=sys.stderr)
            continue
        d = os.path.dirname(os.path.abspath(fp)) or '.'
        groups.setdefault(d, []).append(fp)

    total_downloaded = 0
    for d, fs in groups.items():
        img_dir = os.path.join(d, 'images')
        os.makedirs(img_dir, exist_ok=True)
        url_to_local = {}
        counter = _next_counter(img_dir)
        for fp in fs:
            with open(fp, encoding='utf-8') as f:
                content = f.read()
            matches = collect_images(content)
            if not matches:
                print(f'  no remote images: {os.path.basename(fp)}')
                continue

            referer = build_referer_from_frontmatter(content)
            new_content = content
            for m in reversed(matches):
                url = m['url']
                if url not in url_to_local:
                    counter += 1
                    ext = extract_extension(url)
                    local_name = f'image_{counter:03d}{ext}'
                    try:
                        data = _download(url, referer)
                        with open(os.path.join(img_dir, local_name), 'wb') as wf:
                            wf.write(data)
                        url_to_local[url] = local_name
                        total_downloaded += 1
                        print(f'  [{local_name}] {len(data)} bytes')
                    except Exception as e:
                        url_to_local[url] = None
                        print(f'  FAIL [{url[:60]}]: {e}', file=sys.stderr)
                local_name = url_to_local[url]
                if local_name is None:
                    new_text = f'{m["full_text"]}  <!-- REMOTE_IMAGE:下载失败 -->'
                else:
                    new_text = f'![{m["alt"]}](images/{local_name})'
                new_content = new_content[:m['start']] + new_text + new_content[m['end']:]

            with open(fp, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'  updated: {os.path.basename(fp)}')

    print(f'Done: {total_downloaded} images downloaded')
    return total_downloaded


def main():
    if len(sys.argv) < 2:
        print('Usage: python download_md_images.py <file1.md> [file2.md ...]', file=sys.stderr)
        sys.exit(1)
    localize_files(sys.argv[1:])


if __name__ == '__main__':
    main()
