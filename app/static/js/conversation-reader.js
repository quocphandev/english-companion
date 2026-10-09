// "Đọc hội thoại": read chat messages aloud with the browser's speechSynthesis.
// This file only touches the DOM and the speech API; text and queue rules live in ./speech/.
// Nothing is ever spoken until the user presses a button.
import { ReadingQueue } from "./speech/reading-queue.js";
import { detectLanguage, splitIntoChunks } from "./speech/text.js";
import { SPEECH_LANG, pickVoice } from "./speech/voices.js";

const bar = document.getElementById("reader-bar");
const list = document.getElementById("message-list");

function messageElements() {
  return [...list.querySelectorAll(".message[data-role]")];
}

// Plain data for the queue. Text comes from textContent, never HTML.
function toQueueMessage(element) {
  const text = element.querySelector(".message-text")?.textContent ?? "";
  return {
    role: element.dataset.role,
    chunks: splitIntoChunks(text).map((chunk) => ({ text: chunk, language: detectLanguage(chunk) })),
  };
}

function setupReader() {
  if (!bar || !list || !("speechSynthesis" in window)) return;
  const synth = window.speechSynthesis;
  const playButton = document.getElementById("reader-play");
  const stopButton = document.getElementById("reader-stop");
  const filterSelect = document.getElementById("reader-filter");
  const status = document.getElementById("reader-status");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Chrome may keep speaking after a reload; start from silence.
  synth.cancel();

  let queue = null;
  let elements = []; // DOM element for each queue message, same order
  let highlighted = null;
  let lastAnnouncedIndex = -1;
  // Each reading session gets a number. cancel() can still fire onend/onerror of
  // the old utterance; callbacks from an older session are ignored.
  let session = 0;
  // Keep a reference: Chrome can garbage-collect an utterance and never fire onend.
  let currentUtterance = null;

  function updateVisibility() {
    bar.hidden = messageElements().length === 0;
  }

  function highlight(element) {
    if (highlighted === element) return;
    if (highlighted) {
      highlighted.classList.remove("is-reading");
      highlighted.removeAttribute("aria-current");
    }
    highlighted = element;
    if (element) {
      element.classList.add("is-reading");
      element.setAttribute("aria-current", "true");
      element.scrollIntoView({ block: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
    }
  }

  function setReadingUi(reading) {
    playButton.disabled = reading;
    playButton.setAttribute("aria-pressed", String(reading));
    stopButton.hidden = !reading;
  }

  // Announce only when moving to a new message, not for every sentence.
  function announce(position) {
    if (position.messageIndex === lastAnnouncedIndex) return;
    lastAnnouncedIndex = position.messageIndex;
    const { position: number, total } = queue.progress();
    status.textContent = `Đang đọc tin ${number}/${total}`;
  }

  function speak(position, mySession) {
    if (!position) {
      finish("Đã đọc xong.");
      return;
    }
    highlight(elements[position.messageIndex]);
    announce(position);
    const { chunk } = position;
    const utterance = new SpeechSynthesisUtterance(chunk.text);
    utterance.lang = SPEECH_LANG[chunk.language];
    utterance.voice = pickVoice(synth.getVoices(), chunk.language);
    utterance.onend = () => {
      if (mySession === session) speak(queue.advance(), mySession);
    };
    utterance.onerror = (event) => {
      if (mySession !== session || event.error === "interrupted" || event.error === "canceled") return;
      // Skip a sentence the browser could not say instead of getting stuck.
      speak(queue.advance(), mySession);
    };
    currentUtterance = utterance;
    synth.speak(utterance);
  }

  function start() {
    elements = messageElements();
    queue = new ReadingQueue(elements.map(toQueueMessage), filterSelect.value);
    session += 1;
    lastAnnouncedIndex = -1;
    synth.cancel();
    const first = queue.start();
    if (!first) {
      status.textContent = "Không có tin nhắn nào để đọc với lựa chọn hiện tại.";
      return;
    }
    setReadingUi(true);
    speak(first, session);
  }

  function finish(message) {
    session += 1; // ignore callbacks from the utterance that is ending
    synth.cancel();
    currentUtterance = null;
    queue = null;
    highlight(null);
    setReadingUi(false);
    status.textContent = message;
  }

  function stopIfReading(message = "") {
    if (queue) finish(message);
  }

  playButton.addEventListener("click", start);
  stopButton.addEventListener("click", () => {
    finish("Đã dừng đọc.");
    playButton.focus();
  });
  filterSelect.addEventListener("change", () => {
    // Applies from the next message while reading.
    queue?.setFilter(filterSelect.value);
  });

  // A reply that arrives while reading joins the end of the queue (never auto-played otherwise).
  document.addEventListener("chat:turn-added", (event) => {
    updateVisibility();
    if (!queue) return;
    for (const element of event.detail.turnElement.querySelectorAll(".message[data-role]")) {
      elements.push(element);
      queue.append(toQueueMessage(element));
    }
  });
  document.addEventListener("chat:sending", () => stopIfReading());
  // Leaving or reloading the page, or opening another conversation.
  window.addEventListener("pagehide", () => synth.cancel());

  updateVisibility();
}

setupReader();
