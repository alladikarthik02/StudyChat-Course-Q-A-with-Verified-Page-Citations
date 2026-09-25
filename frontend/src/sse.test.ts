import { expect, test } from "vitest";
import { readEvents } from "./sse";

function wire(items: object[]) {
  return items
    .map((e: any) => `event: ${e.event}\r\ndata: ${JSON.stringify(e)}\r\n\r\n`)
    .join("");
}
function stream(text: string, chunkSize = 1) {
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (let i = 0; i < bytes.length; i += chunkSize)
        controller.enqueue(bytes.slice(i, i + chunkSize));
      controller.close();
    },
  });
}
const start = { event: "start", seq: 1, request_id: "a" };
const abstain = { event: "abstain", seq: 2, request_id: "a" };
const done = { event: "done", seq: 3, request_id: "a", outcome: "abstained" };
test("split UTF-8, CRLF, comments and multiple frames", async () => {
  const items = [
    start,
    { event: "delta", seq: 2, request_id: "a", text: "café 👩‍💻" },
    { event: "error", seq: 3, request_id: "a" },
    { ...done, seq: 4, outcome: "error" },
  ];
  for (const size of [1, 7, 10000]) {
    const output: object[] = [];
    await readEvents(stream(": heartbeat\r\n\r\n" + wire(items), size), (e) =>
      output.push(e),
    );
    expect(output).toEqual(items);
  }
});
test("incomplete connection never succeeds", async () => {
  await expect(
    readEvents(stream(wire([start, abstain])), () => {}),
  ).rejects.toThrow("before completion");
});
test.each([
  [start, { ...abstain, seq: 3 }, done],
  [start, { ...abstain, request_id: "other" }, done],
  [start, done],
  [start, abstain, done, done],
  [start, { ...abstain, event: "delta" }, done],
  [start, start],
])("invalid sequence rejected %#", async (...items) => {
  await expect(readEvents(stream(wire(items)), () => {})).rejects.toThrow();
});
test("valid abstention completes", async () => {
  await expect(
    readEvents(stream(wire([start, abstain, done])), () => {}),
  ).resolves.toBeUndefined();
});
