---
name: changelog-polish
description: Use when the user asks to clean up a changelog or release notes file - reads the file, rewrites each entry as one short sentence in the past tense, and keeps the version order and the existing headings untouched.
---

# Changelog polish

Turn a rough changelog into a consistent one. Every entry keeps its own line; nothing is merged or dropped.

## What to read

Read the changelog file the user names. If the user names a directory, read every `CHANGELOG.md` directly under it and skip anything deeper.

## How to rewrite

- One sentence per entry, past tense, no trailing period.
- Keep the version headings, their order, and their dates exactly as they are.
- Keep every command, path, and identifier exactly as written in the source.
- Put the result back in the same file.

## Entry prefixes

| Prefix | Use for | Example |
|:---|:---|:---|
| Added | new features | Added the `--strict` flag |
| Fixed | bug fixes | Fixed the loader crash on empty config |
| Changed | behaviour changes | Changed the default retry count to three |

## Example

```bash
changelog-polish CHANGELOG.md
```

The command rewrites the file in place, so commit before running it.
