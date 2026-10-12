// "Đọc hội thoại": read chat messages aloud with the browser's speechSynthesis.
// This file only touches the DOM and the speech API; text and queue rules live in ./speech/.
// Nothing is ever spoken until the user presses a button.
import { ReadingQueue } from "./speech/reading-queue.js";
import { detectLanguage, splitIntoChunks } from "./speech/text.js";
import { SPEECH_LANG, pickVoice } from "./speech/voices.js";

const bar = document.getElementById("reader-bar");
const list = document.getElementById("message-list");

const LANGUAGE_NAMES = { en: "tiếng Anh", vi: "tiếng Việt" };
// Errors after which the browser cannot speak at all right now.
const FATAL_SPEECH_ERRORS = ["not-allowed", "synthesis-unavailable", "audio-hardware", "audio-busy"];

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

function showUnsupported() {
  // Chat keeps working; only the reading controls are replaced by a short message.
  for (const control of bar.querySelectorAll("button, label")) control.hidden = true;
  const notice = document.getElementById("reader-notice");
  notice.textContent = "Trình duyệt chưa hỗ trợ đọc.";
  notice.hidden = false;
  bar.hidden = messageElements().length === 0;
}

function setupReader() {
  if (!bar || !list) return;
  if (!("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined") {
    showUnsupported();
    return;
  }
  const synth = window.speechSynthesis;
  const playButton = document.getElementById("reader-play");
  const prevButton = document.getElementById("reader-prev");
  const nextButton = document.getElementById("reader-next");
  const stopButton = document.getElementById("reader-stop");
  const filterSelect = document.getElementById("reader-filter");
  const rateSelect = document.getElementById("reader-rate");
  const status = document.getElementById("reader-status");
  const notice = document.getElementById("reader-notice");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Chrome may keep speaking after a reload; start from silence.
  synth.cancel();

  let state = "idle"; // "idle" | "reading" | "paused"
  let queue = null;
  let elements = []; // DOM element for each queue message, same order
  let highlighted = null;
  // Each reading session gets a number. cancel() can still fire onend/onerror of
  // the old utterance; callbacks from an older session are ignored.
  let session = 0;
  // Keep a reference: Chrome can garbage-collect an utterance and never fire onend.
  let currentUtterance = null;
  const warnedLanguages = new Set();

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

  function setState(next) {
    state = next;
    const active = state !== "idle";
    const labels = { idle: "▶ Đọc hội thoại", reading: "⏸ Tạm dừng", paused: "▶ Tiếp tục" };
    playButton.textContent = labels[state];
    playButton.setAttribute("aria-pressed", String(state === "reading"));
    stopButton.hidden = !active;
    prevButton.hidden = !active;
    nextButton.hidden = !active;
  }

  // Announce only when the message changes or reading is paused, not for every sentence.
  function announce(position) {
    const { position: number, total } = queue.progress();
    const text =
      state === "paused" ? `Đã tạm dừng ở tin ${number}/${total}` : `Đang đọc tin ${number}/${total}`;
    if (status.textContent !== text) status.textContent = text;
    highlight(elements[position.messageIndex]);
  }

  // Default voice when no voice fits: say so once per language, keep reading.
  function voiceFor(language) {
    const voices = synth.getVoices();
    const voice = pickVoice(voices, language);
    if (!voice && voices.length > 0 && !warnedLanguages.has(language)) {
      warnedLanguages.add(language);
      notice.textContent = `Không có giọng ${LANGUAGE_NAMES[language]} trên trình duyệt này, đang dùng giọng mặc định.`;
      notice.hidden = false;
    }
    return voice;
  }

  function speak(position, mySession) {
    if (!position) {
      finish("Đã đọc xong.");
      return;
    }
    announce(position);
    const { chunk } = position;
    const utterance = new SpeechSynthesisUtterance(chunk.text);
    utterance.lang = SPEECH_LANG[chunk.language];
    utterance.voice = voiceFor(chunk.language);
    // Read at speak time, so a new speed applies from the next sentence.
    utterance.rate = Number(rateSelect.value);
    utterance.onend = () => {
      if (mySession === session) speak(queue.advance(), mySession);
    };
    utterance.onerror = (event) => {
      if (mySession !== session || event.error === "interrupted" || event.error === "canceled") return;
      if (FATAL_SPEECH_ERRORS.includes(event.error)) {
        finish("Trình duyệt không đọc được lúc này. Chat vẫn dùng bình thường.");
        return;
      }
      // Skip a sentence the browser could not say instead of getting stuck.
      speak(queue.advance(), mySession);
    };
    currentUtterance = utterance;
    synth.speak(utterance);
  }

  // Start a new speaking session from a position (cancels whatever was playing).
  function playFrom(position) {
    session += 1;
    synth.cancel();
    setState("reading");
    speak(position, session);
  }

  function start() {
    elements = messageElements();
    queue = new ReadingQueue(elements.map(toQueueMessage), filterSelect.value);
    const first = queue.start();
    if (!first) {
      status.textContent = "Không có tin nhắn nào để đọc với lựa chọn hiện tại.";
      return;
    }
    playFrom(first);
  }

  // Our own pause: stop speaking but keep the position; resume repeats that sentence.
  // (speechSynthesis.pause()/resume() are unreliable in Chrome.)
  function pause() {
    session += 1;
    synth.cancel();
    setState("paused");
    announce(queue.current());
  }

  function jump(position) {
    if (!position) {
      finish("Đã đọc xong.");
      return;
    }
    if (state === "paused") {
      announce(position);
    } else {
      playFrom(position);
    }
  }

  function finish(message) {
    session += 1; // ignore callbacks from the utterance that is ending
    synth.cancel();
    currentUtterance = null;
    queue = null;
    highlight(null);
    setState("idle");
    status.textContent = message;
  }

  playButton.addEventListener("click", () => {
    if (state === "idle") start();
    else if (state === "reading") pause();
    else playFrom(queue.current());
  });
  prevButton.addEventListener("click", () => jump(queue.previousMessage()));
  nextButton.addEventListener("click", () => jump(queue.nextMessage()));
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
  document.addEventListener("chat:sending", () => {
    if (state !== "idle") finish("");
  });
  // Leaving or reloading the page, or opening another conversation.
  window.addEventListener("pagehide", () => synth.cancel());

  updateVisibility();
}

setupReader();
