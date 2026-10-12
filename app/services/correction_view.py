"""Build the correction card for one learner message (pure functions, no DB).

The AI returns, for each point, the wrong part (`original_span`) and its fix
(`corrected_text`). Here we find those spans in the learner's sentence to show:
the original with the wrong parts marked, and the corrected sentence with the
changed parts marked. Optional "naturalness" tips are kept apart.
"""

import re

from app.schemas.conversation import CorrectionOut, CorrectionView, Segment

SUGGESTION_CATEGORY = "naturalness"

# (start, end, correction) of a span located in the learner's text.
Match = tuple[int, int, CorrectionOut]


def build_correction_view(
    text: str, corrections: list[CorrectionOut]
) -> CorrectionView | None:
    if not corrections:
        return None
    errors = [c for c in corrections if c.category != SUGGESTION_CATEGORY]
    suggestions = [c for c in corrections if c.category == SUGGESTION_CATEGORY]
    matches = locate_spans(text, errors)
    return CorrectionView(
        original=split_segments(text, matches, use_fix=False),
        corrected=split_segments(text, matches, use_fix=True) if matches else None,
        errors=errors,
        suggestions=suggestions,
    )


def locate_spans(text: str, errors: list[CorrectionOut]) -> list[Match]:
    """Find each error's span in the text, left to right, without overlaps.

    Spans the AI did not copy exactly (even ignoring case) are skipped: they
    still appear in the list of errors, just not inside the sentence.
    """
    matches: list[Match] = []
    for correction in errors:
        span = correction.original_span
        if not span.strip():
            continue
        found = find_free_span(text, span, matches)
        if found is not None:
            matches.append((found[0], found[1], correction))
    return sorted(matches, key=lambda match: match[0])


def find_free_span(text: str, span: str, taken: list[Match]) -> tuple[int, int] | None:
    """First whole-word occurrence of `span` not overlapping a taken range.

    Exact case is preferred; a case-insensitive match is the fallback.
    """
    # Whole words only where the span starts/ends with a letter or digit,
    # so the span "go" does not match inside "going".
    prefix = r"(?<!\w)" if span[0].isalnum() else ""
    suffix = r"(?!\w)" if span[-1].isalnum() else ""
    pattern = prefix + re.escape(span) + suffix
    for flags in (0, re.IGNORECASE):
        for found in re.finditer(pattern, text, flags):
            start, end = found.span()
            if all(end <= s or start >= e for s, e, _ in taken):
                return start, end
    return None


def split_segments(text: str, matches: list[Match], *, use_fix: bool) -> list[Segment]:
    """Cut the text into plain and changed pieces.

    With use_fix=False the changed pieces are the learner's wrong parts;
    with use_fix=True they are replaced by the corrections.
    """
    segments: list[Segment] = []
    position = 0
    for start, end, correction in matches:
        if start > position:
            segments.append(Segment(text=text[position:start]))
        changed = correction.corrected_text if use_fix else text[start:end]
        segments.append(Segment(text=changed, changed=True))
        position = end
    if position < len(text):
        segments.append(Segment(text=text[position:]))
    return segments
