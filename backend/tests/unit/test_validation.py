"""B5 — pure validation/sanitization unit tests (spec §2, §7, gate G10).

Exercises `app.services.validation` directly. Bodies are
`raise NotImplementedError` pending the B5 Developer track.
"""

from __future__ import annotations

import time
from datetime import date

import pytest

from app.services.validation import (
    ValidationError,
    sanitize_for_storage,
    validate_effective_dates,
    validate_proposition_not_empty,
)


def test_sanitize_strips_script_tags_but_preserves_text():
    result = sanitize_for_storage("<script>alert(1)</script>Clause 8.4 controls.")
    assert "<script>" not in result
    assert "Clause 8.4 controls." in result


def test_sanitize_is_a_no_op_on_plain_text():
    plain = "Clause 8.4 creates a limited exception."
    assert sanitize_for_storage(plain) == plain


def test_sanitize_neutralizes_event_handler_attributes():
    result = sanitize_for_storage("<img src=x onerror=alert(1)>")
    assert "onerror" not in result


# --- QA regression (2026-07-26): unclosed-tag bypass ------------------------
#
# `sanitize_for_storage`'s tag stripper is `<[^>]+>`, which requires a
# closing `>` inside the SAME string to recognize and remove a tag. A tag
# with no closing `>` (a well-known regex-sanitizer bypass class — QA
# brief item (b)) survives untouched, including any event-handler
# attribute it carries. Gate G10 requires hostile input be "stored/
# rendered as inert data" regardless of whether the attacker bothers to
# close their tag. These are RED against the current implementation and
# pin the REQUIRED behavior, not the bug.


def test_sanitize_neutralizes_unclosed_tag_with_event_handler():
    result = sanitize_for_storage("<img src=x onerror=alert(1) trailing text with no closing bracket")
    assert "<img" not in result
    assert "onerror" not in result


def test_sanitize_neutralizes_unclosed_tag_even_when_followed_by_more_markup():
    # Realistic shape: the sanitized value is later concatenated into a
    # larger HTML document, so a `>` appearing later in the *page* (not in
    # the user's input) must not "complete" the attacker's tag. The
    # sanitizer must neutralize the open tag using only the text it was
    # given -- it must not rely on a `>` that never arrives.
    result = sanitize_for_storage("<svg onload=alert(document.cookie) foo=bar")
    assert "<svg" not in result
    assert "onload" not in result


def test_sanitize_neutralizes_unclosed_tag_with_single_quoted_attribute():
    # QA cycle-2 regression pin: this quoted-attribute shape already
    # passes against the cycle-1 fix (`_UNCLOSED_TAG_RE`'s
    # `[^\s>]*` attribute-value class happily matches quote characters
    # too) but had no dedicated test of its own -- pinning it so a future
    # change can't silently regress it.
    result = sanitize_for_storage("<img src='x' onerror='alert(1)' trailing prose stays")
    assert "<img" not in result
    assert "onerror" not in result
    assert "trailing prose stays" in result


# --- QA regression (2026-07-26, cycle 2): no-space-before-attribute bypass --
#
# `_UNCLOSED_TAG_RE` requires `\s+` immediately before every `key=value`
# attribute token, so it only recognizes attributes separated from the tag
# name (or from each other) by whitespace. A `/` immediately after the tag
# name with NO whitespace -- e.g. `<img/onerror=alert(1)` -- is a
# well-documented real-world sanitizer-evasion shape (OWASP XSS cheat
# sheet): per the HTML5 tokenizer, a `/` right after the tag name enters
# "self-closing start tag state", and the very next non-`>` character
# (here `o` of `onerror`) is reconsumed in "before attribute name state" --
# so `onerror` IS parsed as a live attribute by real browsers even though
# no whitespace precedes it. The current regex's `\s+` requirement means
# this whole class survives `sanitize_for_storage` untouched. Confirmed
# live via the real API (create/PATCH/revisions/comments/rating-rationale
# all reproduce this -- same shared function). RED against the current
# implementation; pins the REQUIRED behavior, not the bug.


def test_sanitize_neutralizes_unclosed_tag_with_no_space_before_attribute():
    result = sanitize_for_storage("<img/onerror=alert(1) Clause 8.4 still creates the exception.")
    assert "<img" not in result
    assert "onerror" not in result


def test_sanitize_neutralizes_unclosed_svg_with_no_space_before_attribute():
    result = sanitize_for_storage("<svg/onload=alert(document.cookie) Good point.")
    assert "<svg" not in result
    assert "onload" not in result


# --- QA regression (2026-07-26, cycle 2): benign-prose corruption -----------
#
# `_TAG_RE = r"<[^>]+>"` has no concept of "this `<` and that `>` are
# unrelated" -- it strips everything between the FIRST `<` and the very
# next `>` anywhere later in the string, even when both characters are
# ordinary comparison operators in unrelated clauses. Legal/financial
# prose routinely uses both in one sentence (amount thresholds, term
# lengths, date ranges), so this silently deletes legitimate authored
# content -- violating spec §2 ("propositions are stored exactly as
# authored") and the QA brief's explicit benign-preservation requirement.
# Pre-existing in `_TAG_RE` (unchanged by the cycle-1 fix), first caught by
# this adversarial probe. RED against the current implementation; pins the
# REQUIRED behavior (byte-for-byte preservation of benign text), not the
# bug.


def test_sanitize_preserves_prose_with_less_than_and_later_unrelated_greater_than():
    benign = "The threshold is met if the amount is < $500 and the term is > 10 years."
    assert sanitize_for_storage(benign) == benign


def test_sanitize_preserves_prose_with_multiple_unrelated_comparisons():
    benign = "if x < y and y > z then the exception in Clause 3 < Clause 8 applies"
    assert sanitize_for_storage(benign) == benign


# --- QA regression (2026-07-26, cycle 3): CDATA/RCDATA-adjacent-element bypass
#
# `_SanitizingParser._CDATA_CONTENT_TAGS` only suppresses `handle_data` for
# `script`/`style`. But the stdlib `html.parser.HTMLParser` this class is
# built on treats a WIDER set of elements as raw-text containers
# internally: `HTMLParser.CDATA_CONTENT_ELEMENTS` also includes `iframe`,
# `xmp`, `noembed`, `noframes` (their content is tokenized as one opaque
# blob, never sub-parsed for nested tags -- exactly matching how real
# browsers treat these elements), and `HTMLParser.RCDATA_CONTENT_ELEMENTS`
# covers `textarea`/`title` the same way. Because our suppression list
# doesn't match the parser's own raw-text list, a `<script>` payload
# nested inside any of these wrapper elements is delivered to
# `handle_data` as literal, unparsed text -- and since `_cdata_skip_depth`
# never got incremented for the wrapper tag, that text is NOT suppressed:
# it survives `sanitize_for_storage` byte-for-byte, e.g.
# `<iframe><script>alert(1)</script></iframe>` -> `<script>alert(1)</script>`
# stored verbatim. A downstream render of the "sanitized" value would
# execute this. Confirmed live via the real API on all five write paths
# (create, PATCH, revisions, comments, rating-rationale -- all call this
# same shared function). RED against the current implementation; pins the
# REQUIRED behavior (no live-looking markup survives), not the bug.


def test_sanitize_neutralizes_script_nested_inside_iframe():
    result = sanitize_for_storage("<iframe><script>alert(1)</script></iframe>Clause stays.")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_script_nested_inside_textarea():
    result = sanitize_for_storage("<textarea><script>alert(1)</script></textarea>Clause stays.")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_script_nested_inside_title():
    result = sanitize_for_storage("<title><script>alert(1)</script></title>Clause stays.")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_script_nested_inside_noembed():
    result = sanitize_for_storage("<noembed><script>alert(1)</script></noembed>Clause stays.")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_script_nested_inside_noframes():
    result = sanitize_for_storage("<noframes><script>alert(1)</script></noframes>Clause stays.")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_script_nested_inside_xmp():
    result = sanitize_for_storage("<xmp><script>alert(1)</script></xmp>Clause stays.")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_dangerous_tag_nested_inside_iframe_without_script():
    # Not every payload needs an inner <script> -- any tag-shaped content
    # inside the raw-text wrapper survives the same way.
    result = sanitize_for_storage('<iframe><img src=x onerror=alert(1)></iframe>Clause stays.')
    assert "<img" not in result
    assert "onerror" not in result
    assert "Clause stays." in result


# --- QA regression (2026-07-26, cycle 3): second abandoned tag leaks --------
#
# `_salvage_trailing_prose` walks the leftover, unresolved tail from ONE
# abandoned (never-closed) start tag: it strips the tag name plus a run of
# `name=value` attribute tokens, then returns whatever follows untouched.
# When the untouched remainder itself contains a SECOND, independent
# abandoned tag (e.g. two unclosed elements chained back-to-back with no
# `>` anywhere in the whole input), the attribute-token walk correctly
# stops at the second tag's `<` (since `<svg` isn't `key=value`-shaped),
# but the returned "prose tail" then contains that second tag's raw
# opening markup AND its own live-looking attribute verbatim --
# `<img src=x onerror=alert(1) <svg onload=alert(2) trailing` sanitizes to
# ` <svg onload=alert(2) trailing`, i.e. the second tag's `<svg
# onload=alert(2)` survives untouched. Confirmed live via the real API.
# RED against the current implementation; pins the REQUIRED behavior (no
# live-looking tag/attribute text survives), not the bug.


def test_sanitize_neutralizes_second_of_two_chained_abandoned_tags():
    result = sanitize_for_storage(
        "<img src=x onerror=alert(1) <svg onload=alert(2) trailing"
    )
    assert "<img" not in result
    assert "<svg" not in result
    assert "onerror" not in result
    assert "onload" not in result


def test_sanitize_neutralizes_second_of_two_chained_abandoned_tags_same_tag_name():
    result = sanitize_for_storage(
        "<img src=x onerror=alert(1) <img src=y onerror=alert(2) more text"
    )
    assert result.count("<img") == 0
    assert "onerror" not in result


# --- QA regression pins (2026-07-26, cycle 3): confirmed-correct shapes -----
#
# These attack/edge-case shapes were adversarially probed in cycle 3 and
# found already handled correctly by the `html.parser`-based tokenizer.
# Pinned here so a future change to `_SanitizingParser` or
# `_salvage_trailing_prose` can't silently regress them.


def test_sanitize_neutralizes_unclosed_tag_with_quoted_attribute_containing_greater_than():
    # A literal `>` INSIDE a quoted attribute value must not be mistaken
    # for the tag's closing bracket -- the tag stays open past it, exactly
    # as a real browser's tokenizer would treat it.
    result = sanitize_for_storage('<img src="x" onerror="alert(1)>" trailing prose stays')
    assert "<img" not in result
    assert "onerror" not in result
    assert "trailing prose stays" in result


def test_sanitize_neutralizes_closed_tag_with_literal_greater_than_in_attribute_value():
    result = sanitize_for_storage('<img alt="a>b" onerror=alert(1)>Clause stays.')
    assert "<img" not in result
    assert "onerror" not in result
    assert result == "Clause stays."


def test_sanitize_neutralizes_script_with_space_before_closing_bracket():
    # `</script >` (whitespace before `>`) is still a valid closing tag
    # per the HTML5 spec's tag-name-state grammar.
    result = sanitize_for_storage("<script>alert(1)</script >Clause stays.")
    assert "<script" not in result
    assert "alert(1)" not in result
    assert result == "Clause stays."


def test_sanitize_neutralizes_script_with_tab_before_closing_bracket():
    result = sanitize_for_storage("<script>alert(1)</script\t>Clause stays.")
    assert "<script" not in result
    assert "alert(1)" not in result
    assert result == "Clause stays."


def test_sanitize_preserves_section_symbol_and_ampersand():
    benign = "§8.2 & 8.4"
    assert sanitize_for_storage(benign) == benign


def test_sanitize_preserves_curly_quotes_and_em_dash():
    benign = "“The party shall” — as defined herein — comply with §8.2 & 8.4."
    assert sanitize_for_storage(benign) == benign


def test_sanitize_preserves_literal_entity_text_written_by_author():
    benign = "The literal text &amp; appears here, written by the author, not as markup."
    assert sanitize_for_storage(benign) == benign


def test_sanitize_preserves_multi_paragraph_text_with_newlines():
    benign = (
        "Paragraph one, discussing Clause 8.4.\n\n"
        "Paragraph two, discussing Clause 9.1 < Clause 12.\n\n"
        "Paragraph three."
    )
    assert sanitize_for_storage(benign) == benign


# --- QA regression (2026-07-26, cycle 4): convergence-bound bypass ----------
#
# R13's fixpoint driver re-runs `_sanitize_once` until output stabilizes,
# bounded at `_MAX_SANITIZE_PASSES` (8) passes. `_salvage_trailing_prose`
# resolves exactly ONE abandoned (never-closed) tag per pass -- confirmed
# in cycle 3's chained-abandoned-tag fix, which handles a 2-tag chain in
# 2 fixpoint iterations. That fix generalizes correctly (each extra
# chained tag costs exactly one more pass), but the fixed 8-pass ceiling
# is itself an attacker-guessable constant: a chain of MORE than 8
# abandoned tags with live event-handler attributes needs MORE than 8
# passes to fully resolve, so the loop hits its bound before convergence
# and returns an intermediate value that is more sanitized than the raw
# input but still contains a literal, unclosed, live tag -- e.g. a
# 9-element chain leaves `<iframe onload=alert(9)` verbatim in the
# output. Confirmed live via the real API (POST /api/v1/assertions --
# see test_hostile_input.py) as well as at this unit level; a value
# containing an unclosed tag with a live event-handler attribute is
# exactly the shape multiple earlier cycles (1 and 3) already established
# as executable when the stored value is later concatenated into a
# larger HTML document (the tag's `>` is supplied by surrounding markup,
# not by the attacker's input). This is a NEW defect in the bound itself,
# not a new markup shape the fixpoint mechanism fails to recognize -- the
# mechanism is correct; the fixed pass ceiling is not attacker-proof.
# RED against the current implementation; pins the REQUIRED behavior
# (full neutralization regardless of chain depth), not the bug. A chain
# of 7 (comfortably within the 8-pass bound) is pinned alongside it as a
# regression proving shallower/realistic chains are unaffected.


def test_sanitize_convergence_attack_with_nine_chained_abandoned_tags_leaves_no_live_markup():
    chain = " ".join(
        [
            "<img src=x onerror=alert(1)",
            "<svg onload=alert(2)",
            "<body onload=alert(3)",
            "<input onfocus=alert(4) autofocus",
            "<details ontoggle=alert(5) open",
            "<marquee onstart=alert(6)",
            "<video onloadstart=alert(7)",
            "<audio onloadstart=alert(8)",
            "<iframe onload=alert(9)",
        ]
    )
    result = sanitize_for_storage(chain + " trailing text after chain.")
    assert "<iframe" not in result
    assert "<svg" not in result
    assert "<img" not in result
    assert "onload" not in result
    assert "onerror" not in result
    assert "trailing text after chain." in result


def test_sanitize_neutralizes_chain_of_seven_abandoned_tags_within_pass_bound():
    # Regression pin: a chain shallow enough to resolve within the 8-pass
    # bound must still fully sanitize -- the convergence-bound finding
    # above is about exceeding the bound, not about chains in general.
    chain = " ".join(
        [
            "<img src=x onerror=alert(1)",
            "<svg onload=alert(2)",
            "<body onload=alert(3)",
            "<input onfocus=alert(4) autofocus",
            "<details ontoggle=alert(5) open",
            "<marquee onstart=alert(6)",
            "<video onloadstart=alert(7)",
        ]
    )
    result = sanitize_for_storage(chain + " trailing text after chain.")
    assert "<video" not in result
    assert "<marquee" not in result
    assert "onloadstart" not in result
    assert "onstart" not in result
    assert "trailing text after chain." in result


# --- QA regression pins (2026-07-26, cycle 4): confirmed-correct shapes -----
#
# Adversarial round 4 probed wrapper families beyond the raw-text/RCDATA
# element set, comment/CDATA sections, processing instructions/doctypes,
# and entity reassembly. All of the below are already handled correctly
# by the current `html.parser`-based fixpoint -- pinned so future changes
# can't silently regress them.


def test_sanitize_neutralizes_script_nested_inside_template():
    result = sanitize_for_storage("<template><script>alert(1)</script></template>Clause stays.")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_script_after_plaintext():
    # <plaintext> has no end tag at all in real HTML -- everything after
    # it is raw text for the rest of the document. HTMLParser treats it
    # as an ordinary (non-raw-text) start tag, so its "content" is parsed
    # normally and any embedded <script> is stripped like any other tag.
    result = sanitize_for_storage("<plaintext><script>alert(1)</script>Clause stays.")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_script_nested_inside_svg_foreignobject():
    result = sanitize_for_storage(
        "<svg><foreignObject><script>alert(1)</script></foreignObject></svg>Clause stays."
    )
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_script_nested_inside_math():
    result = sanitize_for_storage("<math><script>alert(1)</script></math>Clause stays.")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_script_inside_cdata_section():
    result = sanitize_for_storage("<![CDATA[<script>alert(1)</script>]]>Clause stays.")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_script_after_bogus_comment():
    result = sanitize_for_storage("<!-->Clause stays.<script>alert(1)</script>")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_unterminated_comment_with_embedded_script():
    result = sanitize_for_storage("<!--<script>alert(1)</script>Clause never appears.")
    assert "<script" not in result
    assert "alert(1)" not in result


def test_sanitize_neutralizes_processing_instruction_wrapper():
    result = sanitize_for_storage(
        '<?xml-stylesheet type="text/xsl" href="evil.xsl"?>Clause stays.'
    )
    assert "<?" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_doctype_with_embedded_script():
    result = sanitize_for_storage("<!DOCTYPE html><script>alert(1)</script>Clause stays.")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_preserves_literal_entity_text_that_spells_out_a_tag_name():
    # An author literally typing `&lt;script&gt;` as prose (e.g.
    # documenting an XSS example in a legal memo about a data-breach
    # incident) must survive as that literal text -- it must neither
    # become a live tag NOR be treated as markup and stripped away.
    benign = (
        "&lt;script&gt;alert(1)&lt;/script&gt; is the literal example "
        "text quoted in the incident report."
    )
    assert sanitize_for_storage(benign) == benign


def test_sanitize_preserves_long_multi_paragraph_legal_prose_byte_exact():
    # Data-integrity re-check (cycle 4): long multi-paragraph prose with
    # several </> comparisons, a footnote citation, and a literal &amp;
    # must survive completely unchanged.
    prose = (
        "This Agreement is made as of the Effective Date by and between "
        "the Parties. Section 3.2 provides that the Threshold Amount is "
        "met only if the claim exceeds $500 and the covered term is > 10 "
        "years from the Effective Date; conversely, if the amount is < "
        "$100, the exception in Section 8.4 does not apply.\n\n"
        "Footnote 1: See Smith v. Jones, 123 F.3d 456 (9th Cir. 1999) "
        "(holding that neither inequality, standing alone, triggers the "
        "notice obligation under Clause 8.2). Footnote 2: the parties "
        "acknowledge that 5 < 10 and that 10 > 5.\n\n"
        "The term “Affiliate” & “Subsidiary” shall have the meanings "
        "set forth in Schedule A. This is a literal &amp; ampersand "
        "written by the author, not markup. Section §8.2 & §8.4 both "
        "apply — as defined herein."
    )
    assert sanitize_for_storage(prose) == prose


def test_validate_proposition_not_empty_rejects_blank():
    with pytest.raises(ValidationError):
        validate_proposition_not_empty("   ")


def test_validate_proposition_not_empty_accepts_text():
    validate_proposition_not_empty("A non-empty proposition.")


def test_validate_effective_dates_rejects_end_before_start():
    with pytest.raises(ValidationError):
        validate_effective_dates(date(2026, 1, 1), date(2020, 1, 1))


def test_validate_effective_dates_accepts_open_ended_range():
    validate_effective_dates(date(2020, 1, 1), None)


def test_validate_effective_dates_accepts_none_none():
    validate_effective_dates(None, None)


# --- Post-review independent audit finding (2026-07-26): entity/charref -----
# --- reconstruction corrupts ordinary authored text (R16(a), --------------
# --- AUDIT-FAIL: B5) --------------------------------------------------------
#
# A 4-lens adversarial audit run AFTER QA closed (five cycles clean) found
# that `_SanitizingParser.handle_entityref`/`handle_charref` re-emit
# `f"&{name};"` -- APPENDING a `;` the author never typed. This corrupts
# ordinary, non-adversarial legal/business prose: any bare `&` followed by
# letters/digits that happens to look like an entity or numeric charref
# name gets a semicolon inserted that was never in the source text,
# violating spec §2 ("propositions are stored exactly as authored"). Worse,
# for malformed numeric charrefs shaped `&#<digits><hex-letter>` (e.g.
# `&#160a`, `&#5b`), each fixpoint pass GROWS the text instead of
# shrinking it -- falsifying R14's stated "every changing pass strictly
# shortens" invariant -- so the loop never converges, burns O(n^2) CPU,
# and FAIL-CLOSES per R14: the ENTIRE document is silently destroyed
# (`sanitize_for_storage` returns `""`). Manager-reproduced; see ruling
# R16 and the AUDIT-FAIL entries under Next Steps. RED against the
# current implementation; pins the REQUIRED behavior (byte-exact
# preservation), not the bug.


def test_sanitize_preserves_ampersand_before_letters_byte_exact():
    text = "R&D spend exceeded the cap"
    assert sanitize_for_storage(text) == text


def test_sanitize_preserves_multiple_bare_ampersands_byte_exact():
    text = "AT&T and Johnson & Co"
    assert sanitize_for_storage(text) == text


def test_sanitize_preserves_ampersand_immediately_before_capitalized_word_byte_exact():
    text = "Smith &Jones LLP"
    assert sanitize_for_storage(text) == text


def test_sanitize_preserves_numeric_charref_missing_semicolon_byte_exact():
    text = "Rule 5 &#8212 applies."
    assert sanitize_for_storage(text) == text


def test_sanitize_preserves_malformed_charref_does_not_destroy_document():
    # Worst-case audit finding: this benign sentence was returning `""`
    # (the ENTIRE document destroyed) before the fix, because `&#160a`
    # never converges under the fixpoint driver.
    text = "The nbsp is encoded as &#160a in the export, per Exhibit C."
    result = sanitize_for_storage(text)
    assert result != "", "entire document was destroyed -- see R16(a)"
    assert result == text


def test_sanitize_preserves_short_malformed_charref_does_not_destroy_document():
    text = "Damages of &#5b were awarded."
    result = sanitize_for_storage(text)
    assert result != "", "entire document was destroyed -- see R16(a)"
    assert result == text


def test_sanitize_preserves_escaped_entity_literal_guard():
    # Guard pin: author-written escaped-entity text already passes against
    # the current implementation -- must keep passing once the
    # entity/charref reconstruction bug above is fixed.
    benign = "&lt;script&gt; literal"
    assert sanitize_for_storage(benign) == benign


def test_sanitize_charref_shaped_long_input_converges_promptly_without_destruction():
    # Non-convergence/performance guard: a charref-shaped input at scale
    # must not hit the O(n^2) growing-charref pathology (R16(a)) and must
    # not fail-close to "" per R14 -- it must return promptly and intact.
    text = "&#0a" + "A" * 8000
    start = time.perf_counter()
    result = sanitize_for_storage(text)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.5, (
        f"sanitize_for_storage took {elapsed:.3f}s on a charref-shaped "
        f"8KB input (required: <0.5s) -- see R16(a) growing-charref "
        f"non-convergence."
    )
    assert result != "", "entire document was destroyed -- see R16(a)"


# --- Post-review independent audit finding (2026-07-26): RCDATA content ----
# --- suppression swallows authored prose (R16(b), AUDIT-FAIL: B5) ----------
#
# R13 suppressed `handle_data` output for every raw-text/RCDATA wrapper
# element the installed `HTMLParser` recognizes (title, textarea, iframe,
# xmp, noembed, noframes) as defense in depth. But an UNCLOSED wrapper tag
# appearing in ordinary prose (a `<Title>` or `<textarea>` typed as if it
# were a defined-term placeholder, not markup) causes the parser to treat
# EVERYTHING AFTER IT as that element's suppressed "content" -- silently
# deleting the rest of the authored document. Manager-reproduced; see
# ruling R16(b) and the AUDIT-FAIL entry under Next Steps. Required:
# suppress CONTENT only for `script`/`style`; the existing fixpoint driver
# (R13) neutralizes any nested payload in every other wrapper. Dropping
# just the tag token itself is the accepted known limitation -- losing the
# REST of the sentence is the defect. RED against the current
# implementation; pins the REQUIRED behavior.


def test_sanitize_preserves_prose_after_unclosed_title_tag():
    text = (
        "Signatory: <Title> of the Company. The Company shall pay "
        "$1,000,000 by 1 March 2027."
    )
    result = sanitize_for_storage(text)
    assert "<title" not in result.lower()
    assert "Signatory:" in result
    assert "of the Company." in result
    assert "The Company shall pay $1,000,000 by 1 March 2027." in result


def test_sanitize_preserves_prose_after_unclosed_textarea_tag():
    text = "The <textarea> clause and everything after it."
    result = sanitize_for_storage(text)
    assert "<textarea" not in result.lower()
    assert "clause and everything after it." in result


# --- Audit-finding regression guards (2026-07-26): content safety must -----
# --- stay green while the entity/charref and RCDATA fixes land -------------
#
# R16's fix direction changes two load-bearing behaviors of
# `sanitize_for_storage`: (a) entities/charrefs must no longer be
# reconstructed with an appended `;` -- shielding `&` from the parser
# entirely; and (b) CONTENT suppression for raw-text/RCDATA wrapper
# elements narrows from R13's full list down to just `script`/`style`,
# relying on the existing fixpoint driver (R13/R14) to neutralize any
# nested payload in every other wrapper. These exact attack shapes are
# named in the sprint's Next Steps as required to remain fully
# neutralized -- a fix that restores integrity must not trade away
# safety. No live-looking markup may leak while the fix lands.


_AUDIT_DANGER_MARKERS = ("<script", "<img", "<svg", "onerror=", "onload=", "<iframe")


def _assert_no_audit_danger_markers(result: str) -> None:
    for marker in _AUDIT_DANGER_MARKERS:
        assert marker not in result, f"{marker!r} leaked into sanitized output: {result!r}"


def test_sanitize_guard_script_nested_inside_iframe_stays_neutralized():
    _assert_no_audit_danger_markers(
        sanitize_for_storage("<iframe><script>alert(1)</script></iframe>")
    )


def test_sanitize_guard_script_nested_inside_textarea_stays_neutralized():
    _assert_no_audit_danger_markers(
        sanitize_for_storage("<textarea><script>alert(1)</script></textarea>")
    )


def test_sanitize_guard_img_onerror_nested_inside_title_stays_neutralized():
    _assert_no_audit_danger_markers(
        sanitize_for_storage("<title><img src=x onerror=alert(1)></title>")
    )


def test_sanitize_guard_unclosed_img_with_onerror_stays_neutralized():
    _assert_no_audit_danger_markers(sanitize_for_storage("<img src=x onerror=alert(1)"))


def test_sanitize_guard_no_space_slash_img_onerror_stays_neutralized():
    _assert_no_audit_danger_markers(sanitize_for_storage("<img/onerror=alert(1)"))


def test_sanitize_guard_chained_svg_then_img_abandoned_tags_stays_neutralized():
    _assert_no_audit_danger_markers(
        sanitize_for_storage("<svg onload=alert(1) <img onerror=alert(2)")
    )


def test_sanitize_guard_script_nested_inside_template_stays_neutralized():
    _assert_no_audit_danger_markers(
        sanitize_for_storage("<template><script>alert(1)</script></template>")
    )
