import type { StreamEvent } from "./types";

export async function readEvents(
  stream: ReadableStream<Uint8Array>,
  accept: (event: StreamEvent) => void,
) {
  const reader = stream.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  let buffer = "",
    sequence = 0,
    requestId = "",
    terminal = false,
    phase = "initial";
  function frame(raw: string) {
    const lines = raw.split(/\r?\n/);
    const data = lines
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data) return;
    const item = JSON.parse(data) as StreamEvent;
    const kind = lines
      .find((line) => line.startsWith("event:"))
      ?.slice(6)
      .trim();
    if (
      terminal ||
      kind !== item.event ||
      item.seq !== sequence + 1 ||
      !item.request_id ||
      (requestId && requestId !== item.request_id)
    )
      throw new Error("Invalid stream sequence");
    if (phase === "initial" && item.event !== "start")
      throw new Error("Missing stream start");
    if (item.event === "start") {
      if (phase !== "initial") throw new Error("Duplicate stream start");
      phase = "stream";
    } else if (item.event === "delta") {
      if (phase !== "stream" || typeof item.text !== "string")
        throw new Error("Invalid answer delta");
    } else if (["verification", "abstain", "error"].includes(item.event)) {
      if (phase !== "stream") throw new Error("Invalid stream outcome");
      if (
        item.event === "verification" &&
        (!item.result ||
          typeof item.result.text !== "string" ||
          !Array.isArray(item.result.citations))
      )
        throw new Error("Invalid verification");
      phase = item.event;
    } else if (item.event === "done") {
      if (!["verification", "abstain", "error"].includes(phase))
        throw new Error("Premature completion");
      terminal = true;
    } else throw new Error("Unknown stream event");
    sequence = item.seq;
    requestId = item.request_id;
    accept(item);
  }
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += done
        ? decoder.decode()
        : decoder.decode(value, { stream: true });
      if (buffer.length > 1_000_000) throw new Error("Stream event too large");
      let match: RegExpExecArray | null;
      while ((match = /\r?\n\r?\n/.exec(buffer))) {
        frame(buffer.slice(0, match.index));
        buffer = buffer.slice(match.index + match[0].length);
      }
      if (done) break;
    }
    if (buffer.trim() || !terminal)
      throw new Error("Connection ended before completion");
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
