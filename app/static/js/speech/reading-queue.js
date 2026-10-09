// Pure reading-queue state for "Đọc hội thoại". No DOM and no speech API.
//
// A queue holds messages in conversation order: { role, chunks: [{ text, language }] }.
// The cursor points at one chunk of one message. The filter decides which
// messages are read: "both" (user and chatbot) or "assistant" (chatbot only).

export const READ_FILTERS = ["both", "assistant"];

export class ReadingQueue {
  #messages = [];
  #filter = "both";
  #messageIndex = -1;
  #chunkIndex = 0;

  constructor(messages = [], filter = "both") {
    this.#messages = [...messages];
    this.setFilter(filter);
  }

  get filter() {
    return this.#filter;
  }

  setFilter(filter) {
    if (!READ_FILTERS.includes(filter)) throw new Error(`Unknown read filter: ${filter}`);
    this.#filter = filter;
  }

  /** Add a message at the end (e.g. a reply that arrived while reading). */
  append(message) {
    this.#messages.push(message);
  }

  /** Move to the first readable chunk. Returns the current position, or null if nothing to read. */
  start() {
    this.#messageIndex = this.#nextReadableIndex(0);
    this.#chunkIndex = 0;
    return this.current();
  }

  /** Current position: { messageIndex, chunkIndex, message, chunk }, or null when not reading. */
  current() {
    const message = this.#messages[this.#messageIndex];
    if (!message) return null;
    return {
      messageIndex: this.#messageIndex,
      chunkIndex: this.#chunkIndex,
      message,
      chunk: message.chunks[this.#chunkIndex],
    };
  }

  /** Go to the next chunk, moving on to the next readable message when needed. */
  advance() {
    const message = this.#messages[this.#messageIndex];
    if (!message) return null;
    if (this.#chunkIndex + 1 < message.chunks.length) {
      this.#chunkIndex += 1;
    } else {
      this.#messageIndex = this.#nextReadableIndex(this.#messageIndex + 1);
      this.#chunkIndex = 0;
    }
    return this.current();
  }

  /** Stop reading; the next start() begins from the top again. */
  reset() {
    this.#messageIndex = -1;
    this.#chunkIndex = 0;
  }

  /** "message 2 of 5" among readable messages, for the status line. */
  progress() {
    const readable = this.#readableIndexes();
    return { position: readable.indexOf(this.#messageIndex) + 1, total: readable.length };
  }

  #isReadable(message) {
    return message.chunks.length > 0 && (this.#filter === "both" || message.role === "assistant");
  }

  #nextReadableIndex(from) {
    for (let index = from; index < this.#messages.length; index += 1) {
      if (this.#isReadable(this.#messages[index])) return index;
    }
    return -1;
  }

  #readableIndexes() {
    return this.#messages.flatMap((message, index) => (this.#isReadable(message) ? [index] : []));
  }
}
