import os
import sys
import tempfile
import shutil
import unittest

# Tests live at the repo root; the script is still under plugin/skills/, so go up two levels
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'plugin',
                                'skills', 'download-md-images', 'scripts'))
from download_md_images import (
    find_remote_images,
    find_html_images,
    collect_images,
    extract_extension,
    build_referer_from_frontmatter,
)

FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')


class TestFindRemoteImages(unittest.TestCase):
    def test_finds_standard_image(self):
        content = '![alt](https://example.com/img.png)'
        results = find_remote_images(content)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['url'], 'https://example.com/img.png')
        self.assertEqual(results[0]['alt'], 'alt')

    def test_finds_image_with_title_attr(self):
        content = '![alt](https://example.com/img.png "Chart Title")'
        results = find_remote_images(content)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['url'], 'https://example.com/img.png')
        self.assertEqual(results[0]['alt'], 'alt')

    def test_finds_multiple_images(self):
        content = '''![a](https://a.com/1.png)
        ![b](https://b.com/2.jpg)'''
        results = find_remote_images(content)
        self.assertEqual(len(results), 2)

    def test_dedup_same_url(self):
        content = '''![a](https://x.com/img.png)
        ![b](https://x.com/img.png)'''
        results = find_remote_images(content)
        urls = [r['url'] for r in results]
        self.assertEqual(len(urls), 2)
        # Both should have the same URL (dedup is done later by caller)
        self.assertEqual(urls[0], urls[1])

    def test_ignores_local_images(self):
        content = '![local](images/local.png)'
        results = find_remote_images(content)
        self.assertEqual(len(results), 0)

    def test_no_images_returns_empty(self):
        content = '# Just text\n\nNo images here.'
        results = find_remote_images(content)
        self.assertEqual(len(results), 0)

    def test_preserves_start_position(self):
        content = 'prefix ![a](https://x.com/img.png) suffix'
        results = find_remote_images(content)
        self.assertEqual(len(results), 1)
        start = results[0]['start']
        end = results[0]['end']
        self.assertEqual(content[start:end], '![a](https://x.com/img.png)')


class TestFindHtmlImages(unittest.TestCase):
    def test_finds_html_img(self):
        content = '<img src="https://x.com/img.png" alt="Chart">'
        results = find_html_images(content)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['url'], 'https://x.com/img.png')
        self.assertEqual(results[0]['alt'], 'Chart')

    def test_ignores_non_http_src(self):
        content = '<img src="/local.png" alt="local">'
        self.assertEqual(len(find_html_images(content)), 0)

    def test_extracts_src_with_query(self):
        content = '<img src="https://x.com/a.png?fit=max" alt="">'
        results = find_html_images(content)
        self.assertEqual(results[0]['url'], 'https://x.com/a.png?fit=max')

    def test_missing_alt_defaults_empty(self):
        content = '<img src="https://x.com/a.png">'
        results = find_html_images(content)
        self.assertEqual(results[0]['alt'], '')


class TestCollectImages(unittest.TestCase):
    def test_combines_markdown_and_html_in_order(self):
        content = '![md](https://a.com/1.png) <img src="https://b.com/2.jpg" alt="b">'
        results = collect_images(content)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['url'], 'https://a.com/1.png')
        self.assertEqual(results[1]['url'], 'https://b.com/2.jpg')


class TestExtractExtension(unittest.TestCase):
    def test_png(self):
        self.assertEqual(extract_extension('https://x.com/img.png'), '.png')

    def test_jpg(self):
        self.assertEqual(extract_extension('https://x.com/img.jpg'), '.jpg')

    def test_gif(self):
        self.assertEqual(extract_extension('https://x.com/img.gif'), '.gif')

    def test_no_ext_defaults_to_png(self):
        self.assertEqual(extract_extension('https://x.com/img'), '.png')

    def test_strips_query_string(self):
        self.assertEqual(
            extract_extension('https://x.com/img.png?token=abc'),
            '.png'
        )

    def test_unknown_ext_defaults_to_png(self):
        self.assertEqual(extract_extension('https://x.com/img.xyz'), '.png')


class TestBuildReferer(unittest.TestCase):
    def test_extracts_source_url(self):
        content = '---\ntitle: Test\nsource_url: https://example.com/page\n---\nbody'
        self.assertEqual(
            build_referer_from_frontmatter(content),
            'https://example.com/page'
        )

    def test_no_source_url_returns_empty(self):
        content = '---\ntitle: Test\n---\nbody'
        self.assertEqual(build_referer_from_frontmatter(content), '')

    def test_no_frontmatter_returns_empty(self):
        content = '# Just a title\nbody'
        self.assertEqual(build_referer_from_frontmatter(content), '')


if __name__ == '__main__':
    unittest.main()
