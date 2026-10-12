"""Pure helpers for word lookup (FR05): words, selections and the source sentence.

Offsets are Unicode code point indices (Python str indices), as SPEC section 8
requires; the browser converts from its UTF-16 indices before calling the API.
"""

import re

MAX_SELECTION_WORDS = 8
# A word: letters/digits, keeping inner apostrophes and hyphens (don't, I’m, well-known).
WORD_PATTERN = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*")
# A sentence ends with . ! ? … followed by space, or at a line break.
SENTENCE_BREAK = re.compile(r"(?<=[.!?…])\s+|\n+")


def word_spans(text: str) -> list[tuple[int, int]]:
    """(start, end) of every word; punctuation is never a word on its own."""
    return [match.span() for match in WORD_PATTERN.finditer(text)]


def words_in(text: str, start: int, end: int) -> list[tuple[int, int]]:
    """Words that overlap the selection [start, end)."""
    return [(s, e) for s, e in word_spans(text) if s < end and e > start]


def sentence_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    """Start and end of the sentence(s) containing the selection [start, end)."""
    bounds = []
    position = 0
    for match in SENTENCE_BREAK.finditer(text):
        bounds.append((position, match.start()))
        position = match.end()
    bounds.append((position, len(text)))
    touched = [(s, e) for s, e in bounds if s < end and e > start] or [(0, len(text))]
    return touched[0][0], touched[-1][1]
