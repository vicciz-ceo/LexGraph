"""Shared law-wide instrument vocabulary (sprint 2026-08-04-defs-il,
rulings M16/M17; split out of `il_trigger_grammar.py` in Phase D's D-1a
bundle purely to keep both files under the sprint's 300-line style gate --
no behavior change from the split itself).

`LAW_WIDE_WORDS`/`law_wide_preamble_phrases` -- measured, hand-verified
per phrase (sprint log's Phase C round 2 entry has the full per-phrase
verification transcript) -- instrument words whose preamble genuinely
names the WHOLE law/instrument (`scope="law-wide"`), each with its
`לענין`/`לעניין` preposition variant. Shared between the list-shape
scope-inference table (`il_list_shape_scope.py`) and the quote-first
law-wide rule (`il_m17_spelling_variant_scope_triggers.py`) so the
vocabulary is defined and measured ONCE, not duplicated per grammar
shape. Deliberately EXCLUDES (each verified against real corpus
instances -- see the log): `בתוספת זו` (schedule), `בפוליסה זו` (an
embedded form), `בפרק משנה זה` (sub-chapter), `בנספח זה` (appendix),
`בטבלה זו` (table), `בנוסחה זו` (formula), `בתקנה זאת`/`בתקנת שעת חירום
זו` (article-level, not law-wide), `לעניין כלל זה` (one rule, singular
-- NOT the same as plural `בכללים אלה`), `לעניין פרט חימוש זה`, `באמת
מידה זו`, enumerated multi-article ranges, and `בכלל זה` (a false
friend meaning "including this").

`il_trigger_grammar.py` re-exports `LAW_WIDE_WORDS`/`law_wide_preamble_
phrases` for backward compatibility with every existing importer.
"""

from __future__ import annotations

LAW_WIDE_WORDS: tuple[str, ...] = (
    "חוק זה",
    "חוק יסוד זה",
    "תקנות אלה",
    "תקנות אלו",
    "הסכם זה",
    "כללים אלה",
    "פקודה זו",
    "צו זה",
    "אכרזה זו",
    "נוהל זה",
    # D-1a (sprint 2026-08-04-defs-il, Phase D), M22 correction 2 --
    # independently re-confirmed by this Developer against the real
    # corpus: the זאת register of "פקודה זו". `בפקודה זאת` = 4 files, 2
    # genuinely definitional law-wide preambles (`פקודת הצופים`: `:
    # בפקודה זאת -`; `פקודת האריסים (הגנה)`: `: בפקודה זאת יהיו
    # למונחים... -`), the other 2 referential prose that never ends in a
    # dash (so the list-shape/quote-first mechanisms this vocabulary
    # feeds can never mistake them for a preamble regardless -- verified
    # directly, not merely assumed: both non-definitional dash-ending
    # lines this same word also happens to appear on, elsewhere in the
    # SAME file, are immediately followed by `(א)`/`(ב)`-labelled clause
    # continuations, never `:-`-marked entries, so they produce zero
    # candidates even though their own line coincidentally ends in "-").
    "פקודה זאת",
)

# D-1a, M21/M22: "הכרזה זו" (heh spelling of "אכרזה זו") is DEFINITIONAL
# only in its לענין/לעניין prepositional form -- independently
# re-measured by this Developer against the real corpus (matches M22's
# own correction of M21's stale "measured zero"): `לעניין הכרזה זו` = 3
# files / 3 occurrences, ALL genuine heading-embedded definitional
# preambles (`@ N. ... : לעניין הכרזה זו -`, a Class-C shape); `לענין
# הכרזה זו` = 0; the bare `ב`-form (`בהכרזה זו`) = 2 files / 4
# occurrences, ALL referential prose inside `<מבוא>` clauses (COVID
# declarations), never a definitional preamble, and never even
# dash-terminated (re-confirmed directly, not merely trusted). Kept in a
# SEPARATE table -- not `LAW_WIDE_WORDS` -- specifically so `law_wide_
# preamble_phrases()` never auto-generates the unsafe bare `ב`-form for
# this one word; every `LAW_WIDE_WORDS` entry's `ב`-form has been
# independently verified safe (Phase C round 2), this one has been
# independently verified UNSAFE (the opposite).
LAW_WIDE_PREPOSITION_ONLY_WORDS: tuple[str, ...] = ("הכרזה זו",)

# D-1a, M22 correction 2, honest residual (NOT added anywhere, by
# design): "אכרזה זאת" (the זאת register of "אכרזה זו") is measured
# DEFINITIONAL -- 1 file (`אכרזה על ארגון יציג...`) -- but that one
# occurrence sits entirely inside the article's own HEADING line (`@
# (תיקון: תשפ"ג) : באכרזה זאת, "..." - ...`, a quote-first grammar
# embedded in a heading -- a Class-C-adjacent shape this sprint's Class-C
# fix does NOT reach, since Class C only handles `:-`/`::-` LIST bodies,
# not an inline quote-first clause sitting in the heading itself).
# Neither consumer of this vocabulary (the list-shape body-preamble scan,
# or the M17 quote-first body scan) ever reads heading text, so adding
# this word to either table above would be a permanently-dead entry under
# every rule registered today. Deliberately left OUT rather than added as
# vocabulary theater -- flagged here, and in the sprint log, as a real,
# measured, currently-unreachable gap.


def law_wide_preamble_phrases() -> tuple[str, ...]:
    """Every `<ב-word>` / `לענין <word>` / `לעניין <word>` law-wide
    phrase built from `LAW_WIDE_WORDS`, PLUS the `לענין <word>`/`לעניין
    <word>` (but never bare `ב<word>`) forms built from `LAW_WIDE_
    PREPOSITION_ONLY_WORDS` (D-1a) -- longest-first (defensive against
    substring-shadowing in a linear scope-inference scan, even though no
    actual collision exists among these phrases -- see
    `il_list_shape_scope.py`)."""
    phrases: list[str] = []
    for word in LAW_WIDE_WORDS:
        phrases.append("ב" + word)
        phrases.append("לענין " + word)
        phrases.append("לעניין " + word)
    for word in LAW_WIDE_PREPOSITION_ONLY_WORDS:
        phrases.append("לענין " + word)
        phrases.append("לעניין " + word)
    return tuple(sorted(phrases, key=len, reverse=True))
