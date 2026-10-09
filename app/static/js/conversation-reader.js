// "Đọc hội thoại": read chat messages aloud with the browser's speechSynthesis.
// This file only touches the DOM and the speech API; text rules live in ./speech/.
// Nothing is ever spoken until the user presses a button.
import { detectLanguage, splitIntoChunks } from "./speech/text.js";
import { SPEECH_LANG, pickVoice } from "./speech/voices.js";

const bar = document.getElementById("reader-bar");
const list = document.getElementById("message-list");

function messageElements() {
  return [...list.querySelectorAll(".message[data-role]")];
}

// Text to read: the stored message text from the DOM (textContent, never HTML).
function messageChunks(element) {
  const text = element.querySelector(".message-text")?.textContent ?? "";
  return splitIntoChunks(text).map((chunk) => ({ text: chunk, language: detectLanguage(chunk) }));
}

function setupReader() {
  if (!bar || !list || !("speechSynthesis" in window)) return;
  const synth = window.speechSynthesis;
  const playButton = document.getElementById("reader-play");
  const status = document.getElementById("reader-status");
  // Chrome may keep speaking after a reload; start from silence.
  synth.cancel();

  // Keep a reference: Chrome can garbage-collect an utterance and never fire onend.
  let currentUtterance = null;

  function updateVisibility() {
    bar.hidden = messageElements().length === 0;
  }

  function speakChunks(chunks, onDone) {
    let index = 0;
    const speakNext = () => {
      if (index >= chunks.length) {
        currentUtterance = null;
        onDone();
        return;
      }
      const chunk = chunks[index];
      index += 1;
      const utterance = new SpeechSynthesisUtterance(chunk.text);
      utterance.lang = SPEECH_LANG[chunk.language];
      utterance.voice = pickVoice(synth.getVoices(), chunk.language);
      utterance.onend = speakNext;
      currentUtterance = utterance;
      synth.speak(utterance);
    };
    speakNext();
  }

  playButton.addEventListener("click", () => {
    const first = messageElements()[0];
    if (!first) return;
    synth.cancel();
    status.textContent = "Đang đọc tin 1";
    speakChunks(messageChunks(first), () => {
      status.textContent = "";
    });
  });

  document.addEventListener("chat:turn-added", updateVisibility);
  updateVisibility();
}

setupReader();
