// FR05: click a word (or select a phrase) in a chatbot message to see its meaning
// in that sentence. Text is only ever set with textContent / createElement.
import { phraseRange, toCodePoints, tokenize } from "./tokens.js";

const list = document.getElementById("message-list");
const phraseButton = document.getElementById("phrase-mode");
const MAX_PHRASE_WORDS = 8;
const POS_LABELS = {
  noun: "danh từ",
  verb: "động từ",
  "phrasal verb": "cụm động từ",
  adjective: "tính từ",
  adverb: "trạng từ",
  preposition: "giới từ",
  pronoun: "đại từ",
  conjunction: "liên từ",
  idiom: "thành ngữ",
};

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  let data = null;
  try {
    data = await response.json();
  } catch {
    // keep data null
  }
  return { ok: response.ok, data };
}

// --- Clickable words -----------------------------------------------------------

function wordify(textElement) {
  if (textElement.dataset.wordified) return;
  const fragment = document.createDocumentFragment();
  for (const piece of tokenize(textElement.textContent)) {
    if (!piece.isWord) {
      fragment.append(piece.text);
      continue;
    }
    const word = el("span", "word", piece.text);
    word.tabIndex = 0;
    word.setAttribute("role", "button");
    word.dataset.cpStart = String(piece.cpStart);
    word.dataset.cpEnd = String(piece.cpEnd);
    fragment.append(word);
  }
  textElement.replaceChildren(fragment);
  textElement.dataset.wordified = "true";
}

function wordifyAll(root) {
  for (const text of root.querySelectorAll(".message-assistant[data-message-id] .message-text")) {
    wordify(text);
  }
}

function messageOf(node) {
  return node.closest(".message-assistant[data-message-id]");
}

// --- Result card (inline under the message: never covers the input) ------------

let card = null;

function closeCard() {
  card?.remove();
  card = null;
}

function openCard(message, selectedText) {
  closeCard();
  card = el("section", "lookup-card");
  card.setAttribute("aria-label", `Nghĩa của “${selectedText}”`);
  const header = el("div", "lookup-header");
  header.append(el("strong", "lookup-term", selectedText));
  const close = el("button", "icon-button lookup-close", "✕");
  close.type = "button";
  close.setAttribute("aria-label", "Đóng");
  close.addEventListener("click", closeCard);
  header.append(close);
  const status = el("p", "lookup-status", "Đang tra…");
  status.setAttribute("role", "status");
  card.append(header, status);
  message.after(card);
  return card;
}

function showResult(target, data) {
  target.querySelector(".lookup-status").remove();
  const meta = el("p", "lookup-meta");
  meta.append(el("span", "tag", POS_LABELS[data.pos?.toLowerCase()] ?? data.pos));
  if (data.lemma && data.lemma.toLowerCase() !== data.selected_text.toLowerCase()) {
    meta.append(" Dạng gốc: ", el("strong", "", data.lemma));
  }
  const meaning = el("p", "lookup-meaning", data.meaning_vi);
  const example = el("p", "lookup-example", data.example_en);
  example.lang = "en";
  target.append(meta, meaning, example);
  if (data.uncertainty_vi || data.alternatives.length > 0) {
    const doubt = el("div", "lookup-doubt");
    if (data.uncertainty_vi) doubt.append(el("p", "", `Chưa chắc chắn: ${data.uncertainty_vi}`));
    if (data.alternatives.length > 0) {
      const others = el("ul", "lookup-alternatives");
      for (const option of data.alternatives) {
        others.append(el("li", "", `${option.meaning_vi} (${option.note_vi})`));
      }
      doubt.append(el("p", "", "Cách hiểu khác:"), others);
    }
    target.append(doubt);
  }
  if (data.sentence_meaning_vi) {
    const sentence = el("details", "lookup-sentence");
    sentence.append(el("summary", "", "Nghĩa cả câu"), el("p", "", data.sentence_meaning_vi));
    target.append(sentence);
  }
  target.append(saveForm(data));
}

// FR06: save the word; the meaning can be edited first. On failure the card keeps
// its data so the learner can retry.
function saveForm(data) {
  const form = el("form", "lookup-save");
  form.noValidate = true;
  const inputId = `save-meaning-${data.message_id}-${data.start}`;
  const label = el("label", "", "Nghĩa sẽ lưu (có thể sửa)");
  label.htmlFor = inputId;
  const input = el("input");
  input.id = inputId;
  input.value = data.meaning_vi;
  input.maxLength = 300;
  const button = el("button", "button button-small", "Lưu từ");
  button.type = "submit";
  const status = el("p", "lookup-save-status");
  status.setAttribute("role", "status");
  form.append(label, input, button, status);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const meaning = input.value.trim();
    if (!meaning) {
      status.textContent = "Bạn chưa nhập nghĩa.";
      status.classList.add("is-error");
      return;
    }
    button.disabled = true;
    status.classList.remove("is-error");
    status.textContent = "Đang lưu…";
    try {
      const { ok, data: saved } = await postJson("/api/vocabulary", {
        message_id: data.message_id,
        start: data.start,
        end: data.end,
        meaning_vi: meaning,
      });
      if (ok) {
        status.textContent = saved.created
          ? "Đã lưu vào sổ từ."
          : "Từ này với nghĩa đó đã có trong sổ từ.";
      } else {
        status.textContent = saved?.message_vi ?? "Không lưu được, hãy thử lại.";
        status.classList.add("is-error");
      }
    } catch {
      status.textContent = "Không kết nối được máy chủ, hãy thử lại.";
      status.classList.add("is-error");
    } finally {
      button.disabled = false;
    }
  });
  return form;
}

function showError(target, message) {
  const status = target.querySelector(".lookup-status");
  status.textContent = message;
  status.classList.add("is-error");
}

async function lookup(message, cpStart, cpEnd, label) {
  const target = openCard(message, label);
  const messageId = Number(message.dataset.messageId);
  try {
    const { ok, data } = await postJson("/api/lookup", {
      message_id: messageId,
      start: cpStart,
      end: cpEnd,
    });
    if (card !== target) return; // another lookup replaced this card
    if (ok && data?.status === "succeeded") {
      target.querySelector(".lookup-term").textContent = data.selected_text;
      showResult(target, { ...data, message_id: messageId, start: cpStart, end: cpEnd });
    } else {
      showError(target, data?.error?.message_vi ?? data?.message_vi ?? "Không tra được lúc này.");
    }
  } catch {
    if (card === target) showError(target, "Không kết nối được máy chủ. Hãy thử lại.");
  }
}

// --- Phrase selection ---------------------------------------------------------------

let phraseMode = false;
let phraseStart = null;

function setPhraseMode(on) {
  phraseMode = on;
  phraseStart?.classList.remove("is-phrase-start");
  phraseStart = null;
  if (!phraseButton) return;
  phraseButton.setAttribute("aria-pressed", String(on));
  phraseButton.textContent = on ? "Chạm từ đầu của cụm…" : "Chọn cụm";
}

function wordsBetween(first, second) {
  const words = [...first.parentElement.querySelectorAll(".word")];
  const [a, b] = [words.indexOf(first), words.indexOf(second)].sort((x, y) => x - y);
  return b - a + 1;
}

function onWord(word) {
  const message = messageOf(word);
  if (!message) return;
  if (!phraseMode) {
    lookup(message, Number(word.dataset.cpStart), Number(word.dataset.cpEnd), word.textContent);
    return;
  }
  if (!phraseStart) {
    phraseStart = word;
    word.classList.add("is-phrase-start");
    phraseButton.textContent = "Chạm từ cuối của cụm…";
    return;
  }
  if (messageOf(phraseStart) !== message) {
    // A phrase must stay inside one message: restart from this word.
    phraseStart.classList.remove("is-phrase-start");
    phraseStart = word;
    word.classList.add("is-phrase-start");
    return;
  }
  if (wordsBetween(phraseStart, word) > MAX_PHRASE_WORDS) {
    phraseButton.textContent = `Tối đa ${MAX_PHRASE_WORDS} từ, chọn lại từ cuối…`;
    return;
  }
  const range = phraseRange(
    { cpStart: Number(phraseStart.dataset.cpStart), cpEnd: Number(phraseStart.dataset.cpEnd) },
    { cpStart: Number(word.dataset.cpStart), cpEnd: Number(word.dataset.cpEnd) },
  );
  const text = message.querySelector(".message-text").textContent;
  const label = [...text].slice(range.cpStart, range.cpEnd).join("");
  setPhraseMode(false);
  lookup(message, range.cpStart, range.cpEnd, label);
}

// Desktop: select text with the mouse, then press "Tra cụm".
const selectionButton = el("button", "button button-small lookup-selection", "Tra cụm");
selectionButton.type = "button";
selectionButton.hidden = true;
document.body.append(selectionButton);
let pendingSelection = null;

function selectionInMessage() {
  const selection = window.getSelection();
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) return null;
  const range = selection.getRangeAt(0);
  const startMessage = messageOf(range.startContainer.parentElement ?? range.startContainer);
  const endMessage = messageOf(range.endContainer.parentElement ?? range.endContainer);
  if (!startMessage || startMessage !== endMessage) return null;
  const textElement = startMessage.querySelector(".message-text");
  const before = document.createRange();
  before.selectNodeContents(textElement);
  before.setEnd(range.startContainer, range.startOffset);
  const text = textElement.textContent;
  const startUtf16 = before.toString().length;
  const endUtf16 = startUtf16 + range.toString().length;
  return {
    message: startMessage,
    cpStart: toCodePoints(text, startUtf16),
    cpEnd: toCodePoints(text, endUtf16),
    label: range.toString().trim(),
    rect: range.getBoundingClientRect(),
  };
}

function updateSelectionButton() {
  pendingSelection = selectionInMessage();
  if (!pendingSelection || !pendingSelection.label) {
    selectionButton.hidden = true;
    return;
  }
  // CSSOM changes are allowed by the page's Content-Security-Policy.
  selectionButton.style.top = `${pendingSelection.rect.bottom + 6}px`;
  selectionButton.style.left = `${Math.max(8, pendingSelection.rect.left)}px`;
  selectionButton.hidden = false;
}

function setup() {
  if (!list) return;
  wordifyAll(list);

  list.addEventListener("click", (event) => {
    const word = event.target.closest(".word");
    if (word) onWord(word);
  });
  list.addEventListener("keydown", (event) => {
    const word = event.target.closest(".word");
    if (word && (event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      onWord(word);
    }
  });
  list.addEventListener("mouseup", () => setTimeout(updateSelectionButton, 0));
  document.addEventListener("selectionchange", () => {
    if (window.getSelection()?.isCollapsed) selectionButton.hidden = true;
  });
  selectionButton.addEventListener("click", () => {
    const chosen = pendingSelection;
    selectionButton.hidden = true;
    window.getSelection()?.removeAllRanges();
    if (chosen) lookup(chosen.message, chosen.cpStart, chosen.cpEnd, chosen.label);
  });
  phraseButton?.addEventListener("click", () => setPhraseMode(!phraseMode));

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (phraseMode) setPhraseMode(false);
    closeCard();
  });
  document.addEventListener("click", (event) => {
    if (!card) return;
    const inside = card.contains(event.target) || event.target.closest(".word, .lookup-selection");
    if (!inside) closeCard();
  });
  // New chatbot replies become clickable too.
  document.addEventListener("chat:turn-added", (event) => wordifyAll(event.detail.turnElement));
}

setup();
