import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { detectLanguage, splitIntoChunks } from "../../app/static/js/speech/text.js";

describe("detectLanguage", () => {
  test("plain English is en", () => {
    assert.equal(detectLanguage("Yesterday I went to work."), "en");
  });

  test("Vietnamese with diacritics is vi", () => {
    assert.equal(detectLanguage("Hôm qua tôi đi làm."), "vi");
  });

  test("mostly Vietnamese mixed sentence is vi", () => {
    assert.equal(detectLanguage("Tôi là tester ở công ty"), "vi");
  });

  test("English with one Vietnamese word stays en", () => {
    assert.equal(detectLanguage("I really like phở for breakfast"), "en");
  });

  test("text without letters defaults to en", () => {
    assert.equal(detectLanguage("123 !!!"), "en");
    assert.equal(detectLanguage(""), "en");
  });

  test("uppercase Vietnamese letters are recognised", () => {
    assert.equal(detectLanguage("ĐI ĂN PHỞ"), "vi");
  });
});

describe("splitIntoChunks", () => {
  test("splits on sentence endings and line breaks", () => {
    assert.deepEqual(splitIntoChunks("Hello there! How are you?\nI am fine… Thanks."), [
      "Hello there!",
      "How are you?",
      "I am fine…",
      "Thanks.",
    ]);
  });

  test("keeps decimals and inner dots together", () => {
    assert.deepEqual(splitIntoChunks("It costs 3.5 dollars."), ["It costs 3.5 dollars."]);
  });

  test("drops pieces with nothing to read", () => {
    assert.deepEqual(splitIntoChunks("  ...  \n - \n Hi."), ["Hi."]);
  });

  test("splits a long sentence at commas, packing clauses up to the limit", () => {
    const text = "one two three, four five six, seven eight nine.";
    assert.deepEqual(splitIntoChunks(text, 30), ["one two three, four five six,", "seven eight nine."]);
  });

  test("falls back to words when a clause is still too long", () => {
    const chunks = splitIntoChunks("alpha beta gamma delta epsilon zeta", 12);
    assert.deepEqual(chunks, ["alpha beta", "gamma delta", "epsilon zeta"]);
  });

  test("cuts a single word longer than the limit", () => {
    assert.deepEqual(splitIntoChunks("abcdefghij", 4), ["abcd", "efgh", "ij"]);
  });

  test("every chunk respects the default limit", () => {
    const longText = `${"word ".repeat(200)}end.`;
    for (const chunk of splitIntoChunks(longText)) {
      assert.ok(chunk.length <= 180, `chunk too long: ${chunk.length}`);
    }
  });
});
