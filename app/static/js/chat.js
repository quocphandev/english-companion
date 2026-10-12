// Chat page behaviour: send messages and create conversations with fetch.
// Security rule: user and AI text is only ever set with textContent, never innerHTML.
"use strict";

const CATEGORY_LABELS = {
  grammar: "Ngữ pháp",
  word_choice: "Dùng từ",
  spelling: "Chính tả",
  naturalness: "Tự nhiên hơn",
};
const MESSAGES = {
  emptyText: "Bạn chưa nhập nội dung.",
  emptyTopic: "Bạn chưa nhập chủ đề.",
  sending: "Đang xử lý…",
  stillPending: "Câu này vẫn đang được xử lý ở lần gửi trước. Vui lòng đợi rồi thử lại.",
  network: "Không kết nối được máy chủ. Kiểm tra app còn chạy rồi thử lại.",
  generic: "Đã có lỗi xảy ra. Vui lòng thử lại.",
};

function createElement(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
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
    // Non-JSON body (e.g. a proxy error page): treat as a generic error.
  }
  return { ok: response.ok, data };
}

function errorMessage(data) {
  return data?.error?.message_vi ?? data?.message_vi ?? MESSAGES.generic;
}

// --- Rendering (same structure as the render_turn macro in _macros.html) ---

function renderUserMessage(text, note) {
  const box = createElement("div", "message message-user");
  box.dataset.role = "user";
  box.append(createElement("p", "message-text", text));
  if (note) box.append(createElement("p", "message-note", note));
  return box;
}

function renderSegments(segments, tag) {
  const container = createElement("dd");
  for (const segment of segments) {
    container.append(segment.changed ? createElement(tag, "", segment.text) : segment.text);
  }
  return container;
}

function renderItems(items) {
  const list = createElement("ul", "correction-list");
  for (const item of items) {
    const row = createElement("li", "correction-item");
    row.append(
      createElement("span", "tag", CATEGORY_LABELS[item.category] ?? item.category),
      " ",
      createElement("del", "", item.original_span),
      " → ",
      createElement("ins", "", item.corrected_text),
      createElement("p", "correction-explanation", item.explanation_vi),
    );
    list.append(row);
  }
  return list;
}

// Learning mode: open right away. Conversation mode: closed, the summary is "Xem lỗi".
function renderCorrectionCard(view, mode) {
  const count = view.errors.length + view.suggestions.length;
  const hasErrors = view.errors.length > 0;
  const label =
    mode === "learning"
      ? hasErrors ? "Gợi ý sửa" : "Gợi ý diễn đạt (tùy chọn)"
      : hasErrors ? "Xem lỗi" : "Xem gợi ý";
  const card = createElement("details", `correction-card correction-card-${mode}`);
  card.open = mode === "learning";
  card.append(createElement("summary", "", `${label} (${count})`));
  if (view.corrected) {
    const sentences = createElement("dl", "correction-sentences");
    sentences.append(
      createElement("dt", "", "Câu gốc"),
      renderSegments(view.original, "del"),
      createElement("dt", "", "Câu sửa"),
      renderSegments(view.corrected, "ins"),
    );
    card.append(sentences);
  }
  if (hasErrors) card.append(renderItems(view.errors));
  if (view.suggestions.length > 0) {
    const section = createElement("section", "correction-suggestions");
    section.append(
      createElement("h3", "correction-subheading", "Gợi ý diễn đạt tự nhiên hơn (tùy chọn)"),
      renderItems(view.suggestions),
    );
    card.append(section);
  }
  return card;
}

function renderTurn(turn, mode) {
  const article = createElement("article", "turn");
  article.append(renderUserMessage(turn.message.text));
  if (turn.correction_view) article.append(renderCorrectionCard(turn.correction_view, mode));
  if (turn.reply) {
    const reply = createElement("div", "message message-assistant");
    reply.dataset.role = "assistant";
    reply.dataset.messageId = String(turn.reply.id);
    reply.append(createElement("p", "message-text", turn.reply.text));
    article.append(reply);
  }
  return article;
}

function renderPendingTurn(text) {
  const article = createElement("article", "turn is-pending");
  article.append(renderUserMessage(text, MESSAGES.sending));
  return article;
}

// --- Sending messages ---

function setupComposer() {
  const form = document.getElementById("message-form");
  if (!form) return;
  const input = document.getElementById("message-input");
  const button = document.getElementById("send-button");
  const status = document.getElementById("composer-status");
  const list = document.getElementById("message-list");
  const conversationId = form.dataset.conversationId;

  // Remembers a send that did not succeed, so retrying the same text reuses
  // its request_id and the server never creates a second turn.
  let lastAttempt = null;
  let isSending = false;

  function setStatus(text, isError) {
    status.textContent = text;
    status.classList.toggle("is-error", Boolean(isError));
  }

  function setBusy(busy) {
    isSending = busy;
    button.disabled = busy;
    input.readOnly = busy;
    form.setAttribute("aria-busy", String(busy));
  }

  function scrollToBottom() {
    list.scrollTop = list.scrollHeight;
  }

  async function send() {
    if (isSending) return;
    const text = input.value;
    if (!text.trim()) {
      setStatus(MESSAGES.emptyText, true);
      input.focus();
      return;
    }
    const requestId =
      lastAttempt && lastAttempt.text === text ? lastAttempt.requestId : crypto.randomUUID();
    lastAttempt = { requestId, text };

    // Let other scripts (the conversation reader) react before anything changes.
    document.dispatchEvent(new CustomEvent("chat:sending"));
    // Everything up to the fetch runs synchronously, so the busy state shows at once.
    setBusy(true);
    setStatus(MESSAGES.sending, false);
    document.getElementById("empty-hint")?.remove();
    const pendingTurn = renderPendingTurn(text);
    list.append(pendingTurn);
    scrollToBottom();

    try {
      const { ok, data } = await postJson(`/api/conversations/${conversationId}/messages`, {
        request_id: requestId,
        text,
        input_mode: "text",
      });
      if (ok && data?.status === "succeeded") {
        const turnElement = renderTurn(data, form.dataset.correctionMode);
        pendingTurn.replaceWith(turnElement);
        document.dispatchEvent(new CustomEvent("chat:turn-added", { detail: { turnElement } }));
        input.value = "";
        lastAttempt = null;
        setStatus("", false);
      } else {
        // Keep the typed text in the input so the user can retry or edit it.
        pendingTurn.remove();
        const message = ok && data?.status === "pending" ? MESSAGES.stillPending : errorMessage(data);
        setStatus(message, true);
      }
    } catch {
      pendingTurn.remove();
      setStatus(MESSAGES.network, true);
    } finally {
      setBusy(false);
      input.focus();
      scrollToBottom();
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    send();
  });
  input.addEventListener("keydown", (event) => {
    // isComposing: do not send while a Vietnamese input method is still composing.
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      send();
    }
  });
  scrollToBottom();
}

// --- Creating a conversation ---

function setupNewConversation() {
  const dialog = document.getElementById("new-conversation-dialog");
  const form = document.getElementById("new-conversation-form");
  const error = document.getElementById("new-conversation-error");
  const submitButton = form.querySelector('button[type="submit"]');

  for (const opener of document.querySelectorAll(".js-open-new-conversation")) {
    opener.addEventListener("click", () => {
      error.textContent = "";
      dialog.showModal();
      form.elements.topic.focus();
    });
  }
  form.querySelector(".js-close-dialog").addEventListener("click", () => dialog.close());
  // Clicking the backdrop (outside the form) closes the dialog; Escape works natively.
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const topic = form.elements.topic.value.trim();
    if (!topic) {
      error.textContent = MESSAGES.emptyTopic;
      form.elements.topic.focus();
      return;
    }
    submitButton.disabled = true;
    error.textContent = "";
    try {
      const { ok, data } = await postJson("/api/conversations", {
        topic,
        level: form.elements.level.value,
        correction_mode: form.elements.correction_mode.value,
      });
      if (ok) {
        window.location.href = `/conversations/${data.conversation_id}`;
        return;
      }
      error.textContent = errorMessage(data);
    } catch {
      error.textContent = MESSAGES.network;
    } finally {
      submitButton.disabled = false;
    }
  });
}

// --- Mobile drawer for the sidebar (CSS only shows the toggle on small screens) ---

function setupMobileNav() {
  const layout = document.querySelector(".layout");
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.querySelector(".sidebar-backdrop");
  const toggles = document.querySelectorAll(".js-open-nav");
  if (!layout || !sidebar || !backdrop) return;
  let lastToggle = null;

  function setOpen(open) {
    layout.classList.toggle("nav-open", open);
    backdrop.hidden = !open;
    for (const toggle of toggles) toggle.setAttribute("aria-expanded", String(open));
  }

  for (const toggle of toggles) {
    toggle.addEventListener("click", () => {
      lastToggle = toggle;
      setOpen(true);
      // Wait one frame: the drawer must be visible before it can take focus.
      requestAnimationFrame(() => sidebar.querySelector("a, button")?.focus());
    });
  }
  for (const closer of document.querySelectorAll(".js-close-nav")) {
    closer.addEventListener("click", () => {
      setOpen(false);
      lastToggle?.focus();
    });
  }
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && layout.classList.contains("nav-open")) {
      setOpen(false);
      lastToggle?.focus();
    }
  });
  // Opening the "new conversation" dialog from the drawer: close the drawer first.
  for (const opener of sidebar.querySelectorAll(".js-open-new-conversation")) {
    opener.addEventListener("click", () => setOpen(false));
  }
}

// --- "Giúp tôi" (FR03): suggestions are only inserted, never sent (AC07) ---

function setupHelp() {
  const panel = document.getElementById("help-panel");
  const toggle = document.getElementById("help-toggle");
  const form = document.getElementById("message-form");
  if (!panel || !toggle || !form) return;
  const messageInput = document.getElementById("message-input");
  const intentForm = document.getElementById("help-intent-form");
  const intentInput = document.getElementById("help-intent");
  const status = document.getElementById("help-status");
  const result = document.getElementById("help-result");
  const hint = document.getElementById("help-hint");
  const words = document.getElementById("help-words");
  const explanation = document.getElementById("help-explanation");
  const insertButton = document.getElementById("help-insert");
  const actionButtons = [...panel.querySelectorAll("[data-help-level], #help-intent-form button")];
  const conversationId = Number(form.dataset.conversationId);
  let isLoading = false;

  function setOpen(open) {
    panel.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    if (open) panel.querySelector("[data-help-level]")?.focus();
  }

  function setStatus(text, isError) {
    status.textContent = text;
    status.classList.toggle("is-error", Boolean(isError));
  }

  function showSuggestion(data) {
    hint.textContent = data.hint_en;
    words.replaceChildren(
      ...data.words.map((word) => createElement("li", "", `${word.text}: ${word.meaning_vi}`)),
    );
    explanation.textContent = data.explanation_vi ?? "";
    result.hidden = false;
  }

  async function requestHelp(level, intentVi) {
    if (isLoading) return;
    isLoading = true;
    for (const button of actionButtons) button.disabled = true;
    result.hidden = true;
    setStatus("Đang tìm gợi ý…", false);
    try {
      const { ok, data } = await postJson("/api/help", {
        conversation_id: conversationId,
        level,
        intent_vi: intentVi || null,
      });
      if (ok && data?.status === "succeeded") {
        setStatus("", false);
        showSuggestion(data);
      } else {
        setStatus(errorMessage(data), true);
      }
    } catch {
      setStatus(MESSAGES.network, true);
    } finally {
      isLoading = false;
      for (const button of actionButtons) button.disabled = false;
    }
  }

  toggle.addEventListener("click", () => setOpen(panel.hidden));
  panel.querySelector(".js-close-help").addEventListener("click", () => {
    setOpen(false);
    toggle.focus();
  });
  for (const button of panel.querySelectorAll("[data-help-level]")) {
    button.addEventListener("click", () => requestHelp(Number(button.dataset.helpLevel)));
  }
  intentForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const idea = intentInput.value.trim();
    if (!idea) {
      setStatus("Bạn chưa nhập ý muốn nói.", true);
      intentInput.focus();
      return;
    }
    requestHelp(3, idea);
  });
  // Insert only: the learner edits the text and presses "Gửi" themselves.
  insertButton.addEventListener("click", () => {
    const current = messageInput.value.trimEnd();
    messageInput.value = current ? `${current} ${hint.textContent}` : hint.textContent;
    setOpen(false);
    messageInput.focus();
    messageInput.setSelectionRange(messageInput.value.length, messageInput.value.length);
  });
  panel.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setOpen(false);
      toggle.focus();
    }
  });
}

setupComposer();
setupNewConversation();
setupMobileNav();
setupHelp();
