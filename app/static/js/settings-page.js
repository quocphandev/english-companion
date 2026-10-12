// "Xóa toàn bộ dữ liệu học": requires typing the confirmation phrase.

const form = document.getElementById("delete-all-form");
const status = document.getElementById("delete-all-status");

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector("button");
  button.disabled = true;
  status.textContent = "";
  try {
    const response = await fetch("/api/data/delete-all", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirm: form.elements.confirm.value }),
    });
    if (response.ok) {
      window.location.href = "/";
      return;
    }
    const data = await response.json().catch(() => null);
    status.textContent = data?.message_vi ?? "Không xóa được, hãy thử lại.";
  } catch {
    status.textContent = "Không kết nối được máy chủ.";
  }
  button.disabled = false;
});
