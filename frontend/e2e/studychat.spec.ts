import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
const pdf = readFileSync("../tmp/demo-physics.pdf");

test.beforeEach(async ({ request }) => {
  const docs = await (
    await request.get("http://127.0.0.1:8000/documents")
  ).json();
  for (const doc of docs)
    await request.delete(`http://127.0.0.1:8000/documents/${doc.id}`);
});
async function upload(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByLabel("Upload PDF").setInputFiles({
    name: "physics.pdf",
    mimeType: "application/pdf",
    buffer: pdf,
  });
  await expect(page.getByText("2 pages · ready")).toBeVisible();
  await expect(page.getByLabel("Select physics.pdf")).toBeChecked();
}
test("upload, stream, verify, open actual PDF and highlight quote", async ({
  page,
}) => {
  await upload(page);
  await page.getByLabel("Ask about your PDFs").fill("What is inertia?");
  await page.getByRole("button", { name: "Ask ↗" }).click();
  await expect(
    page.getByText("Citations checked · review the source"),
  ).toBeVisible();
  await page.getByRole("button", { name: /Page 2.*Exact quote match/ }).click();
  await expect(page.getByText("Physical page 2")).toBeVisible();
  await expect(page.getByText("Quote highlighted on this page")).toBeVisible();
  await expect(page.getByLabel("PDF page 2", { exact: true })).toBeVisible();
  await expect(page.locator(".quote-highlight")).not.toHaveCount(0);
  await page.screenshot({ path: "../tmp/studychat-t5.png", fullPage: true });
  await page.getByRole("button", { name: "Close source viewer" }).click();
  await page.getByRole("button", { name: "Delete physics.pdf" }).click();
  await expect(page.getByLabel("Select physics.pdf")).toHaveCount(0);
});
test("invalid citations and HTML are displayed as text, never executable", async ({
  page,
}) => {
  await upload(page);
  const rows = [
    { event: "start" },
    { event: "delta", text: '<img src=x onerror=alert(1)> [D9 p.9 "fake"]' },
    {
      event: "verification",
      result: {
        text: "<img src=x onerror=alert(1)> [citation removed]",
        has_verified_citations: false,
        citations: [
          {
            status: "removed",
            reason: "unknown_document",
            citation: { page: 9, raw: "D9", quote: "fake" },
          },
        ],
      },
    },
    { event: "done", outcome: "no_verified_citations" },
  ];
  await page.route("**/api/chat", (route) =>
    route.fulfill({
      contentType: "text/event-stream",
      body: rows
        .map(
          (e, i) =>
            `event: ${e.event}\ndata: ${JSON.stringify({ ...e, seq: i + 1, request_id: "test" })}\n\n`,
        )
        .join(""),
    }),
  );
  await page.getByLabel("Ask about your PDFs").fill("Explain");
  await page.getByRole("button", { name: "Ask ↗" }).click();
  await expect(
    page.getByText("No verified citations", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".answer-text")).toContainText("<img");
  await expect(page.locator(".answer img")).toHaveCount(0);
  await expect(page.locator(".citation-chip")).toHaveCount(0);
});
test("interrupted stream cannot expose a verified chip", async ({ page }) => {
  await upload(page);
  await page.route("**/api/chat", (route) =>
    route.fulfill({
      contentType: "text/event-stream",
      body: 'event: start\ndata: {"event":"start","seq":1,"request_id":"a"}\n\nevent: delta\ndata: {"event":"delta","seq":2,"request_id":"a","text":"partial"}\n\n',
    }),
  );
  await page.getByLabel("Ask about your PDFs").fill("Explain");
  await page.getByRole("button", { name: "Ask ↗" }).click();
  await expect(
    page.getByText("Interrupted · text is unverified"),
  ).toBeVisible();
  await expect(page.locator(".citation-chip")).toHaveCount(0);
});
test("keyboard submit and cancellation leave provisional text unverified", async ({
  page,
}) => {
  await upload(page);
  await page.getByLabel("Ask about your PDFs").fill("What is gravity?");
  await page.getByRole("button", { name: "Ask ↗" }).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Stop", exact: true }).click();
  await expect(page.getByText("Cancelled · text is unverified")).toBeVisible();
  await expect(page.locator(".citation-chip")).toHaveCount(0);
});
test("ambiguous quote keeps the page and shows highlight fallback", async ({
  page,
  request,
}) => {
  await upload(page);
  const docs = await (
    await request.get("http://127.0.0.1:8000/documents")
  ).json();
  const citation = {
    status: "exact",
    document_id: docs[0].id,
    matched_text: "Gravity",
    ambiguous: true,
    citation: { page: 1, raw: '[D1 p.1 "Gravity"]', quote: "Gravity" },
  };
  const rows = [
    { event: "start" },
    {
      event: "verification",
      result: {
        text: "Gravity",
        has_verified_citations: true,
        citations: [citation],
      },
    },
    { event: "done", outcome: "answered" },
  ];
  await page.route("**/api/chat", (route) =>
    route.fulfill({
      contentType: "text/event-stream",
      body: rows
        .map(
          (e, i) =>
            `event: ${e.event}\ndata: ${JSON.stringify({ ...e, seq: i + 1, request_id: "test" })}\n\n`,
        )
        .join(""),
    }),
  );
  await page.getByLabel("Ask about your PDFs").fill("Gravity");
  await page.getByRole("button", { name: "Ask ↗" }).click();
  await page.getByRole("button", { name: /Page 1.*Exact quote match/ }).click();
  await expect(
    page.getByText("Highlight unavailable or ambiguous. Read the quote below."),
  ).toBeVisible();
  await expect(page.locator(".quote-highlight")).toHaveCount(0);
});

test("reader scrolling up is preserved during a long stream", async ({
  page,
}) => {
  await upload(page);
  await page.evaluate(() => {
    const original = window.fetch;
    window.fetch = async (input, init) => {
      if (String(input) !== "/api/chat") return original(input, init);
      const encoder = new TextEncoder();
      let seq = 0;
      const stream = new ReadableStream<Uint8Array>({
        start(controller) {
          const emit = (event: string, text?: string) =>
            controller.enqueue(
              encoder.encode(
                `event: ${event}\ndata: ${JSON.stringify({ event, text, seq: ++seq, request_id: "scroll-test" })}\n\n`,
              ),
            );
          emit("start");
          const timer = setInterval(
            () =>
              emit(
                "delta",
                "A long provisional explanation about the source.\n".repeat(5),
              ),
            30,
          );
          init?.signal?.addEventListener("abort", () => {
            clearInterval(timer);
            controller.error(new DOMException("Cancelled", "AbortError"));
          });
        },
      });
      return new Response(stream, {
        headers: { "Content-Type": "text/event-stream" },
      });
    };
  });
  await page.getByLabel("Ask about your PDFs").fill("Explain in detail");
  await page.getByRole("button", { name: "Ask ↗" }).click();
  await expect
    .poll(() =>
      page
        .locator(".chat-scroll")
        .evaluate((el) => el.scrollHeight > el.clientHeight + 200),
    )
    .toBeTruthy();
  await page.locator(".chat-scroll").evaluate((el) => {
    el.scrollTop = 0;
    el.dispatchEvent(new Event("scroll"));
  });
  await expect
    .poll(() => page.locator(".answer-text").textContent())
    .toContain("source.");
  await page.waitForTimeout(180);
  expect(
    await page.locator(".chat-scroll").evaluate((el) => el.scrollTop),
  ).toBe(0);
  await expect(page.locator(".citation-chip")).toHaveCount(0);
  await page.getByRole("button", { name: "Stop", exact: true }).click();
  await expect(page.getByText("Cancelled · text is unverified")).toBeVisible();
});

test("mobile library and composer remain within the viewport", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await upload(page);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await expect(page.getByLabel("Ask about your PDFs")).toBeVisible();
});
