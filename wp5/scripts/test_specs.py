"""Link integrity for the specification documents one directory up.

These documents cross-reference each other heavily and cite each other's
headings. A stale link reads exactly like a correct one, so it survives
review; this test is what turns that into a loud failure.
"""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
MD_FILES = sorted(ROOT.glob("*.md"))

HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
LINK = re.compile(r"\]\(([^)\s]+)\)")
EXTERNAL = ("http://", "https://", "mailto:", "#!")


def slug(title):
    """Approximate the GitHub heading-slug rule."""
    s = re.sub(r"[`*_]", "", title.strip().lower())
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"\s+", "-", s.strip())


def slugs_of(path):
    text = path.read_text(encoding="utf-8")
    return [slug(m.group(2)) for m in HEADING.finditer(text)]


def test_markdown_files_found():
    assert MD_FILES, f"no markdown files found in {ROOT}"


def test_heading_slugs_are_unique():
    problems = []
    for path in MD_FILES:
        seen = set()
        for s in slugs_of(path):
            if s in seen:
                problems.append(f"{path.name}: duplicate heading slug '{s}'")
            seen.add(s)
    assert not problems, "\n".join(problems)


def test_links_resolve():
    """Every in-file anchor and every cross-file link points at something real."""
    problems = []
    for path in MD_FILES:
        own = set(slugs_of(path))
        for target in LINK.findall(path.read_text(encoding="utf-8")):
            if target.startswith(EXTERNAL):
                continue
            file_part, _, fragment = target.partition("#")
            if not file_part:  # same-file anchor
                if fragment not in own:
                    problems.append(f"{path.name}: anchor '#{fragment}' has no heading")
                continue
            dest = (path.parent / file_part).resolve()
            if not dest.exists():
                problems.append(f"{path.name}: link target '{file_part}' does not exist")
            elif fragment and dest.suffix == ".md" and fragment not in set(slugs_of(dest)):
                problems.append(f"{path.name}: '{file_part}#{fragment}' has no such heading")
    assert not problems, "\n".join(problems)
