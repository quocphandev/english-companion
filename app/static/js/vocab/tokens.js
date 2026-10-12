// Pure helpers for clickable words (FR05). No DOM: tested with node --test.
//
// The API works in Unicode code points (like Python), while JavaScript strings
// index UTF-16 code units; an emoji is 1 code point but 2 code units.

// Same rule as app/services/text_selection.py: letters/digits, keeping inner
// apostrophes and hyphens (don't, I’m, well-known). Punctuation is never a word.
const WORD_PATTERN = /[\p{L}\p{N}]+(?:['’-][\p{L}\p{N}]+)*/gu;

/** Code point offset of a UTF-16 index inside `text`. */
export function toCodePoints(text, utf16Index) {
  return [...text.slice(0, utf16Index)].length;
}

/**
 * Split text into pieces: { text, isWord, cpStart, cpEnd }.
 * Joining every piece's text gives back the original text.
 */
export function tokenize(text) {
  const pieces = [];
  let position = 0;
  let codePoints = 0;
  const push = (piece, isWord) => {
    const length = [...piece].length;
    pieces.push({ text: piece, isWord, cpStart: codePoints, cpEnd: codePoints + length });
    codePoints += length;
  };
  for (const match of text.matchAll(WORD_PATTERN)) {
    if (match.index > position) push(text.slice(position, match.index), false);
    push(match[0], true);
    position = match.index + match[0].length;
  }
  if (position < text.length) push(text.slice(position), false);
  return pieces;
}

/** Words between two clicked words (inclusive, any order) as one code point range. */
export function phraseRange(first, second) {
  return {
    cpStart: Math.min(first.cpStart, second.cpStart),
    cpEnd: Math.max(first.cpEnd, second.cpEnd),
  };
}
