// Pure text helpers for read-aloud. No DOM and no speech API, so they run under node --test.

// Letters that only appear in Vietnamese (plus vowels carrying Vietnamese tone marks).
const VIETNAMESE_LETTERS =
  /[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]/iu;
// Share of words with Vietnamese letters needed to call a text Vietnamese.
const VIETNAMESE_WORD_RATIO = 0.4;
export const DEFAULT_MAX_CHUNK_LENGTH = 180;

/**
 * Guess the language of a short text: "vi" or "en".
 * Simple rule: Vietnamese if at least 40% of the words contain a Vietnamese letter.
 */
export function detectLanguage(text) {
  const words = text.match(/\p{L}+/gu) ?? [];
  if (words.length === 0) return "en";
  const vietnameseWords = words.filter((word) => VIETNAMESE_LETTERS.test(word)).length;
  return vietnameseWords / words.length >= VIETNAMESE_WORD_RATIO ? "vi" : "en";
}

/**
 * Split text into short pieces (sentences, then clauses, then words) of at most
 * maxLength characters. Long utterances can be cut off silently by some browsers.
 */
export function splitIntoChunks(text, maxLength = DEFAULT_MAX_CHUNK_LENGTH) {
  const sentences = text
    .split(/(?<=[.!?…])\s+|\n+/u)
    .map((sentence) => sentence.trim())
    // Skip pieces with nothing to pronounce, e.g. "..." or "-".
    .filter((sentence) => /[\p{L}\p{N}]/u.test(sentence));
  return sentences.flatMap((sentence) =>
    sentence.length <= maxLength ? [sentence] : splitLongSentence(sentence, maxLength),
  );
}

function splitLongSentence(sentence, maxLength) {
  const clauses = sentence
    .split(/(?<=[,;:])\s+/u)
    .flatMap((clause) => (clause.length <= maxLength ? [clause] : splitByWords(clause, maxLength)));
  return packPieces(clauses, maxLength);
}

function splitByWords(clause, maxLength) {
  const words = clause.split(/\s+/u).flatMap((word) => cutLongWord(word, maxLength));
  return packPieces(words, maxLength);
}

function cutLongWord(word, maxLength) {
  const pieces = [];
  for (let start = 0; start < word.length; start += maxLength) {
    pieces.push(word.slice(start, start + maxLength));
  }
  return pieces;
}

// Join neighbouring pieces with spaces while the result stays within maxLength.
function packPieces(pieces, maxLength) {
  const chunks = [];
  let current = "";
  for (const piece of pieces) {
    const candidate = current ? `${current} ${piece}` : piece;
    if (candidate.length <= maxLength) {
      current = candidate;
    } else {
      if (current) chunks.push(current);
      current = piece;
    }
  }
  if (current) chunks.push(current);
  return chunks;
}
