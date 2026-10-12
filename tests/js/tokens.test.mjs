import assert from "node:assert/strict";
import { test } from "node:test";

import { phraseRange, toCodePoints, tokenize } from "../../app/static/js/vocab/tokens.js";

const words = (text) => tokenize(text).filter((piece) => piece.isWord).map((piece) => piece.text);

test("punctuation is not a word and apostrophes stay inside words", () => {
  assert.deepEqual(words("Don't stop, I’m testing it!"), ["Don't", "stop", "I’m", "testing", "it"]);
});

test("hyphenated and Vietnamese words are kept whole", () => {
  assert.deepEqual(words("A well-known bug. Tôi đi làm."), ["A", "well-known", "bug", "Tôi", "đi", "làm"]);
});

test("pieces join back to the original text", () => {
  const text = "  Hello, world!  ";
  assert.equal(tokenize(text).map((piece) => piece.text).join(""), text);
});

test("offsets are code points, matching the server", () => {
  const book = tokenize("😀 I read a book.").find((piece) => piece.text === "book");
  assert.deepEqual([book.cpStart, book.cpEnd], [11, 15]);
});

test("toCodePoints converts a UTF-16 index", () => {
  const text = "😀 book";
  assert.equal(text.indexOf("book"), 3); // UTF-16
  assert.equal(toCodePoints(text, 3), 2); // code points
});

test("phraseRange works whichever word is clicked first", () => {
  const [looks, , after] = tokenize("looks after").map((piece) => piece);
  assert.deepEqual(phraseRange(after, looks), { cpStart: 0, cpEnd: 11 });
});
