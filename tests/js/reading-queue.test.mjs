import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { ReadingQueue } from "../../app/static/js/speech/reading-queue.js";

const message = (role, ...texts) => ({
  role,
  chunks: texts.map((text) => ({ text, language: "en" })),
});

// Read everything from start() to the end and list the chunk texts.
function readAll(queue) {
  const spoken = [];
  for (let position = queue.start(); position; position = queue.advance()) {
    spoken.push(position.chunk.text);
  }
  return spoken;
}

describe("ReadingQueue", () => {
  test("reads every chunk of every message in order", () => {
    const queue = new ReadingQueue([
      message("user", "Hi.", "I am Quoc."),
      message("assistant", "Hello!"),
      message("user", "Bye."),
    ]);

    assert.deepEqual(readAll(queue), ["Hi.", "I am Quoc.", "Hello!", "Bye."]);
  });

  test("assistant filter skips user messages", () => {
    const queue = new ReadingQueue(
      [message("user", "Hi."), message("assistant", "Hello!"), message("user", "Bye."), message("assistant", "See you.")],
      "assistant",
    );

    assert.deepEqual(readAll(queue), ["Hello!", "See you."]);
  });

  test("messages without chunks are skipped", () => {
    const queue = new ReadingQueue([message("user"), message("assistant", "Hello!")]);

    assert.deepEqual(readAll(queue), ["Hello!"]);
  });

  test("start returns null when nothing is readable", () => {
    assert.equal(new ReadingQueue([]).start(), null);
    assert.equal(new ReadingQueue([message("user", "Hi.")], "assistant").start(), null);
  });

  test("appending while reading puts the new message at the end of the queue", () => {
    const queue = new ReadingQueue([message("user", "Hi."), message("assistant", "Hello!")]);
    const spoken = [queue.start().chunk.text];

    queue.append(message("assistant", "New reply."));
    for (let position = queue.advance(); position; position = queue.advance()) {
      spoken.push(position.chunk.text);
    }

    assert.deepEqual(spoken, ["Hi.", "Hello!", "New reply."]);
  });

  test("changing the filter while reading applies to the following messages", () => {
    const queue = new ReadingQueue([message("user", "Hi."), message("user", "Again."), message("assistant", "Hello!")]);
    queue.start();

    queue.setFilter("assistant");

    assert.equal(queue.advance().chunk.text, "Hello!");
  });

  test("progress counts readable messages only", () => {
    const queue = new ReadingQueue(
      [message("user", "Hi."), message("assistant", "One."), message("user", "Ok."), message("assistant", "Two.")],
      "assistant",
    );
    queue.start();
    assert.deepEqual(queue.progress(), { position: 1, total: 2 });
    queue.advance();
    assert.deepEqual(queue.progress(), { position: 2, total: 2 });
  });

  test("current position exposes the message index for highlighting", () => {
    const queue = new ReadingQueue([message("user", "Hi."), message("assistant", "Hello!")], "assistant");

    assert.equal(queue.start().messageIndex, 1);
  });

  test("reset makes the next start begin from the top", () => {
    const queue = new ReadingQueue([message("user", "Hi."), message("assistant", "Hello!")]);
    queue.start();
    queue.advance();

    queue.reset();

    assert.equal(queue.current(), null);
    assert.equal(queue.start().chunk.text, "Hi.");
  });

  test("an unknown filter is rejected", () => {
    assert.throws(() => new ReadingQueue([], "everyone"), /Unknown read filter/);
  });
});
