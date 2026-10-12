// FR06: edit a note or delete a saved word (with confirmation) on the vocabulary page.

async function sendJson(method, url, body) {
  const response = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try {
    data = response.status === 204 ? null : await response.json();
  } catch {
    // keep data null
  }
  return { ok: response.ok, data };
}

function setStatus(item, text, isError) {
  const status = item.querySelector(".vocab-status");
  status.textContent = text;
  status.classList.toggle("is-error", Boolean(isError));
}

function setup() {
  const list = document.getElementById("vocab-list");
  const dialog = document.getElementById("delete-word-dialog");
  if (!list || !dialog) return;
  let pendingDelete = null;

  list.addEventListener("submit", async (event) => {
    const form = event.target.closest(".vocab-note-form");
    if (!form) return;
    event.preventDefault();
    const item = form.closest(".vocab-item");
    setStatus(item, "Đang lưu…", false);
    try {
      const { ok, data } = await sendJson("PATCH", `/api/vocabulary/${item.dataset.wordId}`, {
        note: form.elements.note.value,
      });
      setStatus(item, ok ? "Đã lưu ghi chú." : (data?.message_vi ?? "Không lưu được."), !ok);
    } catch {
      setStatus(item, "Không kết nối được máy chủ.", true);
    }
  });

  list.addEventListener("click", (event) => {
    const button = event.target.closest(".js-delete-word");
    if (!button) return;
    pendingDelete = button.closest(".vocab-item");
    document.getElementById("delete-word-name").textContent =
      pendingDelete.querySelector(".vocab-lemma").textContent;
    dialog.showModal();
  });

  // The dialog's form uses method="dialog": the pressed button's value becomes returnValue.
  dialog.addEventListener("close", async () => {
    const item = pendingDelete;
    pendingDelete = null;
    if (!item || dialog.returnValue !== "confirm") return;
    try {
      const { ok, data } = await sendJson("DELETE", `/api/vocabulary/${item.dataset.wordId}`);
      if (ok) item.remove();
      else setStatus(item, data?.message_vi ?? "Không xóa được.", true);
    } catch {
      setStatus(item, "Không kết nối được máy chủ.", true);
    }
  });
}

setup();
