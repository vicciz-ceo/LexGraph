"""Stage 1 -- locate articles and definitions sections (sprint
2026-07-29-definition-links, item DL3).

Scope only, not yet terms -- see the review doc's "Deterministic
definition-linking design" Stage 1. `Article` here is a lightweight
parsing-only shape, distinct from `app.models.article.Article` (the ORM
model persisted by `ingest.py`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# `@ <number>. <heading>` marker -- number is one or more digits optionally
# followed by Hebrew letters (construct-numbered sections like `34כד`,
# `51א`, `8א`, `35א`). A literal `.` must follow the number for this to be
# a real article marker -- this excludes stray bracketed page/column
# markers like `@ [יד]` (no trailing period), which are left as ordinary
# body text of whichever article they fall inside.
_ARTICLE_MARKER_RE = re.compile(r"^@\s+(?P<number>\d+[א-ת]*)\.\s*(?P<heading>.*)$")

# A bare `@` marker -- no number, no trailing period, nothing else on the
# line (sprint 2026-08-04-defs-core-scope, manager ruling M8(a)). 124 of
# 6,133 real israeli-laws-wiki documents use a bare `@` as their section
# marker for at least one section; without this branch, such a line falls
# through to the ordinary body-text case below and its whole section
# (including any definitions inside it) is silently merged into whichever
# article/section happens to be open -- or, for a document that uses ONLY
# bare `@` markers, `current_number` never becomes non-`None` at all and
# `parse_articles` returns an empty list, dropping the entire document.
# Deliberately anchored to the WHOLE line (`$`) so it never matches a
# marker that legitimately carries trailing content, e.g. `@ [יד]`.
_BARE_ARTICLE_MARKER_RE = re.compile(r"^@\s*$")

# A `==...==` (chapter) or `===...===` (subsection/"סימן") heading line.
# Both END an article's body scope; only the double-equals ("==", not
# "===") form updates the tracked `.chapter` (a subsection nested under a
# chapter does not itself change the chapter).
_HEADING_BREAK_RE = re.compile(r"^(={2,})\s*(.+?)\s*\1$")

# Stage 1.1's observed definitions-heading forms, matched at the start of
# the (already marker-stripped) heading text, followed by whitespace,
# an opening paren/bracket (trailing annotations like "(תיקון: ...)" or
# "[א/5]"), or end-of-string.
_DEFINITIONS_HEADING_RE = re.compile(
    r"^(הגדרות ופירוש|הגדרת מונחים|הגדרות|הגדרה)(?:\s|\(|\[|$)"
)


@dataclass(frozen=True)
class Article:
    """A parsed article/section -- Stage 1's output shape.

    NOT the ORM model (`app.models.article.Article`); this is a pure
    parsing-time value object.
    """

    number: str
    heading: str
    body: str
    chapter: str | None = None


def is_definitions_heading(heading: str) -> bool:
    """True when `heading` matches one of the known definitions-section
    heading forms (`הגדרות`, `הגדרת מונחים`, `הגדרה`, `הגדרות ופירוש`).
    """
    return bool(_DEFINITIONS_HEADING_RE.match(heading.strip()))


def parse_articles(text: str) -> list[Article]:
    """Split `text` into `Article`s on `@ N.` markers.

    An article's body runs from its own `@ N.` line to the next `@ N.`
    line, or to a `==`/`===` heading-break line, whichever comes first.
    `.chapter` tracks the nearest PRECEDING `==` (double-equals only,
    not `===`) chapter heading's text.
    """
    lines = text.split("\n")

    articles: list[Article] = []
    current_number: str | None = None
    current_heading: str = ""
    current_body_lines: list[str] = []
    current_chapter: str | None = None
    bare_marker_count = 0

    def _flush() -> None:
        if current_number is not None:
            articles.append(
                Article(
                    number=current_number,
                    heading=current_heading,
                    body="\n".join(current_body_lines).strip("\n"),
                    chapter=current_chapter,
                )
            )

    for line in lines:
        marker_match = _ARTICLE_MARKER_RE.match(line)
        if marker_match:
            _flush()
            current_number = marker_match.group("number")
            current_heading = marker_match.group("heading").strip()
            current_body_lines = []
            continue

        if _BARE_ARTICLE_MARKER_RE.match(line):
            # A bare `@` still starts its OWN new section -- it must never
            # fall through to the ordinary body-text branch below (M8(a)).
            # It has no number of its own, so a synthetic, non-colliding
            # placeholder (never matches `_ARTICLE_MARKER_RE`'s
            # `\d+[א-ת]*` number shape) identifies it.
            _flush()
            bare_marker_count += 1
            current_number = f"@{bare_marker_count}"
            current_heading = ""
            current_body_lines = []
            continue

        break_match = _HEADING_BREAK_RE.match(line.strip())
        if break_match:
            _flush()
            current_number = None
            current_heading = ""
            current_body_lines = []
            if len(break_match.group(1)) == 2:
                current_chapter = break_match.group(2)
            continue

        if current_number is not None:
            current_body_lines.append(line)

    _flush()
    return articles


def locate_definitions_sections(articles: list[Article]) -> list[Article]:
    """Return only the articles whose heading is a definitions-heading form.

    Does NOT assume section 1 -- some laws (e.g. חוק העונשין) have many
    definitions sections scattered across chapters.
    """
    return [a for a in articles if is_definitions_heading(a.heading)]
