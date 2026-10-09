import assert from "node:assert/strict";
import { test } from "node:test";

import { pickVoice } from "../../app/static/js/speech/voices.js";

const voice = (name, lang) => ({ name, lang });

test("English prefers en-US over en-GB", () => {
  const voices = [voice("UK", "en-GB"), voice("US", "en-US"), voice("VN", "vi-VN")];
  assert.equal(pickVoice(voices, "en").name, "US");
});

test("English falls back to en-GB, then to any en-*", () => {
  assert.equal(pickVoice([voice("UK", "en-GB"), voice("AU", "en-AU")], "en").name, "UK");
  assert.equal(pickVoice([voice("AU", "en-AU")], "en").name, "AU");
});

test("Vietnamese picks vi-VN", () => {
  const voices = [voice("US", "en-US"), voice("VN", "vi-VN")];
  assert.equal(pickVoice(voices, "vi").name, "VN");
});

test("underscore and lowercase language tags are accepted", () => {
  assert.equal(pickVoice([voice("Android", "vi_vn")], "vi").name, "Android");
});

test("returns null when no voice fits", () => {
  assert.equal(pickVoice([voice("US", "en-US")], "vi"), null);
  assert.equal(pickVoice([], "en"), null);
});
