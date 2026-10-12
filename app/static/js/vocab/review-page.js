// FR07: manual flashcards. Reveal the meaning, then answer "Nhớ" or "Chưa nhớ".

function setup() {
  const deck = document.getElementById("review-deck");
  if (!deck) return;
  const cards = [...deck.querySelectorAll(".flashcard")];
  const progress = document.getElementById("review-progress");
  const done = document.getElementById("review-done");
  const summary = document.getElementById("review-summary");
  const counts = { remembered: 0, again: 0 };
  let index = 0;

  function show(next) {
    cards[index].hidden = true;
    index = next;
    if (index >= cards.length) {
      progress.textContent = "";
      summary.textContent = `Đã ôn ${counts.remembered + counts.again} từ: ${counts.remembered} nhớ, ${counts.again} chưa nhớ.`;
      done.hidden = false;
      done.querySelector("a").focus();
      return;
    }
    cards[index].hidden = false;
    progress.textContent = `Thẻ ${index + 1}/${cards.length}`;
    cards[index].querySelector(".js-reveal").focus();
  }

  deck.addEventListener("click", async (event) => {
    const card = event.target.closest(".flashcard");
    if (!card) return;
    if (event.target.closest(".js-reveal")) {
      event.target.closest(".js-reveal").hidden = true;
      const back = card.querySelector(".flashcard-back");
      back.hidden = false;
      back.querySelector(".js-answer").focus();
      return;
    }
    const answer = event.target.closest(".js-answer");
    if (!answer) return;
    const status = card.querySelector(".flashcard-status");
    const buttons = card.querySelectorAll(".js-answer");
    for (const button of buttons) button.disabled = true;
    status.textContent = "";
    try {
      const response = await fetch("/api/reviews", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vocabulary_id: Number(card.dataset.wordId),
          outcome: answer.dataset.outcome,
        }),
      });
      if (!response.ok) throw new Error("save failed");
      counts[answer.dataset.outcome] += 1;
      show(index + 1);
    } catch {
      // Keep the card so the learner can answer again.
      status.textContent = "Không lưu được kết quả, hãy thử lại.";
    } finally {
      for (const button of buttons) button.disabled = false;
    }
  });
}

setup();
