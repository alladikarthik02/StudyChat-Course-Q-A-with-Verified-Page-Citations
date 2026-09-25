import { StrictMode, Suspense, lazy, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
const PdfViewer = lazy(() =>
  import("./PdfViewer").then((module) => ({ default: module.PdfViewer })),
);
import { readEvents } from "./sse";
import type {
  Citation,
  DocumentInfo,
  Verification,
  ViewerTarget,
} from "./types";
import "./style.css";

type Turn = {
  id: string;
  question: string;
  text: string;
  status: string;
  result?: Verification;
};
type Config = {
  provider_mode: string;
  transmits_content: boolean;
  threshold_label: string;
};
async function check(response: Response) {
  if (response.ok) return response;
  const data = await response.json().catch(() => ({}));
  throw new Error(
    typeof data.detail === "string"
      ? data.detail.replaceAll("_", " ")
      : `Request failed (${response.status})`,
  );
}

function App() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]),
    [selected, setSelected] = useState<string[]>([]);
  const [config, setConfig] = useState<Config | null>(null),
    [consent, setConsent] = useState(false);
  const [question, setQuestion] = useState(""),
    [turns, setTurns] = useState<Turn[]>([]);
  const [error, setError] = useState(""),
    [uploading, setUploading] = useState(false),
    [streaming, setStreaming] = useState(false);
  const [target, setTarget] = useState<ViewerTarget | null>(null);
  const controller = useRef<AbortController | null>(null),
    chatScroll = useRef<HTMLDivElement>(null),
    follow = useRef(true);
  const permitted = !!config && (!config.transmits_content || consent);
  useEffect(() => {
    const abort = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const [docs, cfg] = await Promise.all([
          fetch("/api/documents", { signal: abort.signal })
            .then(check)
            .then((r) => r.json()),
          fetch("/api/config", { signal: abort.signal })
            .then(check)
            .then((r) => r.json()),
        ]);
        setDocuments(docs);
        setConfig(cfg);
      } catch (e) {
        if (!abort.signal.aborted)
          setError(e instanceof Error ? e.message : "Connection failed");
      }
      if (!abort.signal.aborted) timer = setTimeout(poll, 1500);
    }
    void poll();
    return () => {
      abort.abort();
      clearTimeout(timer);
      controller.current?.abort();
    };
  }, []);
  useEffect(() => {
    const el = chatScroll.current;
    if (el && follow.current) el.scrollTop = el.scrollHeight;
  }, [turns]);
  async function upload(file?: File) {
    if (!file) return;
    if (file.size > 20 * 1024 * 1024) {
      setError("Please choose a PDF smaller than 20 MiB.");
      return;
    }
    setUploading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const data = await fetch("/api/documents", {
        method: "POST",
        body: form,
        headers: consent ? { "X-StudyChat-Consent": "yes" } : {},
      })
        .then(check)
        .then((r) => r.json());
      setSelected((ids) => [...ids, data.id].slice(-10));
      setDocuments((docs) => [
        {
          id: data.id,
          filename: file.name,
          state: "processing",
          page_count: 0,
          error_code: null,
        },
        ...docs,
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }
  async function remove(doc: DocumentInfo) {
    setError("");
    try {
      await fetch(`/api/documents/${doc.id}`, { method: "DELETE" }).then(check);
      setDocuments((docs) => docs.filter((d) => d.id !== doc.id));
      setSelected((ids) => ids.filter((id) => id !== doc.id));
      if (target?.documentId === doc.id) setTarget(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }
  function openCitation(citation: Citation) {
    if (citation.document_id && citation.status !== "removed")
      setTarget({
        documentId: citation.document_id,
        page: citation.citation.page,
        quote: citation.matched_text || citation.citation.quote,
        ambiguous: citation.ambiguous,
      });
  }
  async function ask(event: React.FormEvent) {
    event.preventDefault();
    if (!question.trim() || streaming) return;
    const ids = selected.filter((id) =>
      documents.some((d) => d.id === id && d.state === "ready"),
    );
    if (!ids.length) return;
    const id = crypto.randomUUID(),
      prompt = question;
    const abort = new AbortController();
    controller.current = abort;
    setQuestion("");
    setStreaming(true);
    setError("");
    follow.current = true;
    setTurns((old) => [
      ...old,
      { id, question: prompt, text: "", status: "Finding relevant pages…" },
    ]);
    function update(patch: Partial<Turn>) {
      setTurns((old) => old.map((t) => (t.id === id ? { ...t, ...patch } : t)));
    }
    let answer = "",
      verified: Verification | undefined,
      outcome = "",
      failure = "";
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: prompt,
          document_ids: ids,
          live_consent: consent,
        }),
        signal: abort.signal,
      }).then(check);
      if (!response.body) throw new Error("Streaming is unavailable");
      await readEvents(response.body, (item) => {
        if (item.event === "delta") {
          answer += item.text!;
          update({
            text: answer,
            status: "Provisional · checking citations after the stream",
          });
        }
        if (item.event === "verification") verified = item.result;
        if (item.event === "abstain")
          update({
            text: "I could not find enough supporting context in the selected PDFs.",
            status: "Insufficient context",
          });
        if (item.event === "error")
          failure = item.code?.replaceAll("_", " ") || "Generation failed";
        if (item.event === "done") outcome = item.outcome || "";
      });
      if (failure || outcome === "error")
        throw new Error(failure || "Generation failed");
      if (verified)
        update({
          text: verified.text,
          result: verified,
          status: verified.has_verified_citations
            ? "Citations checked · review the source"
            : "No verified citations",
        });
      else if (outcome !== "abstained")
        throw new Error("No final verification received");
    } catch (e) {
      update({
        result: undefined,
        status: abort.signal.aborted
          ? "Cancelled · text is unverified"
          : "Interrupted · text is unverified",
      });
      if (!abort.signal.aborted)
        setError(e instanceof Error ? e.message : "Chat failed");
    } finally {
      setStreaming(false);
      controller.current = null;
    }
  }
  const readySelected = selected.filter((id) =>
    documents.some((d) => d.id === id && d.state === "ready"),
  );
  return (
    <div className={`workspace ${target ? "with-source" : ""}`}>
      <header className="topbar">
        <a className="brand" href="/">
          ◈ <span>StudyChat</span>
        </a>
        <span className="mode">
          {config?.provider_mode === "live"
            ? "OpenAI · live mode"
            : "Offline fixture mode"}
        </span>
      </header>
      <aside className="library">
        <p className="eyebrow">YOUR LIBRARY</p>
        <h2>Course materials</h2>
        <p className="muted">Choose the pages your answers come from.</p>
        {config?.transmits_content && (
          <label className="consent">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />{" "}
            I agree to send PDF text and questions to OpenAI.
          </label>
        )}
        <label
          className={`upload ${!permitted || uploading ? "disabled" : ""}`}
        >
          <span>＋ Add a PDF</span>
          <small>{uploading ? "Uploading…" : "Text PDFs · up to 20 MiB"}</small>
          <input
            aria-label="Upload PDF"
            type="file"
            accept="application/pdf,.pdf"
            disabled={!permitted || uploading}
            onChange={(e) => {
              void upload(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
        </label>
        <ul className="documents">
          {documents.map((doc) => (
            <li key={doc.id}>
              <div className="document-row">
                <input
                  aria-label={`Select ${doc.filename}`}
                  type="checkbox"
                  checked={selected.includes(doc.id)}
                  disabled={streaming || doc.state !== "ready"}
                  onChange={(e) =>
                    setSelected((ids) =>
                      e.target.checked
                        ? [...ids, doc.id].slice(-10)
                        : ids.filter((id) => id !== doc.id),
                    )
                  }
                />
                <div>
                  <strong>{doc.filename}</strong>
                  <small>
                    {doc.state === "ready"
                      ? `${doc.page_count} pages · ready`
                      : doc.error_code?.replaceAll("_", " ") || doc.state}
                  </small>
                </div>
                <button
                  aria-label={`Delete ${doc.filename}`}
                  className="delete"
                  disabled={streaming}
                  onClick={() => void remove(doc)}
                >
                  ×
                </button>
              </div>
            </li>
          ))}
        </ul>
        {!documents.length && (
          <p className="empty-library">
            Your PDFs will appear here.
            <br />
            Start with a lecture or a reading.
          </p>
        )}
        <div className="library-note">
          <strong>Evidence, a click away.</strong>
          <p>
            Citation checks match quoted text to a page. They do not guarantee
            that an answer is correct.
          </p>
        </div>
      </aside>
      <main className="conversation">
        <div className="chat-heading">
          <div>
            <p className="eyebrow">READ. ASK. CHECK.</p>
            <h1>A clearer way to study.</h1>
          </div>
          <span className="selection-count">
            {readySelected.length} selected
          </span>
        </div>
        <div
          className="chat-scroll"
          ref={chatScroll}
          onScroll={() => {
            const el = chatScroll.current!;
            follow.current =
              el.scrollHeight - el.scrollTop - el.clientHeight < 40;
          }}
        >
          {!turns.length && (
            <div className="welcome">
              <span className="welcome-symbol">↗</span>
              <h2>
                Go from a question
                <br />
                to the source.
              </h2>
              <p>
                Add a course PDF, select it, and ask about what you’re reading.
                Each checked citation takes you back to the page.
              </p>
              <div className="steps">
                <span>01 · Add material</span>
                <span>02 · Ask a question</span>
                <span>03 · Check the quote</span>
              </div>
            </div>
          )}
          {turns.map((turn) => (
            <article className="turn" key={turn.id}>
              <div className="question">
                <span>YOU</span>
                <p>{turn.question}</p>
              </div>
              <div className="answer">
                <span>STUDYCHAT</span>
                <p className="answer-status" role="status">
                  {turn.status}
                </p>
                <div className="answer-text">{turn.text}</div>
                {turn.result && (
                  <div className="citations">
                    {turn.result.citations.map((citation, index) =>
                      citation.status === "removed" ? (
                        <span className="removed" key={index}>
                          Citation removed
                        </span>
                      ) : (
                        <button
                          className="citation-chip"
                          key={index}
                          onClick={() => openCitation(citation)}
                        >
                          {citation.status === "exact" ? "✓" : "≈"}{" "}
                          {citation.citation.raw.match(/D\d+/)?.[0]} · Page{" "}
                          {citation.citation.page}
                          <small>
                            {citation.status === "exact"
                              ? "Exact quote match"
                              : "Approximate quote match"}
                          </small>
                        </button>
                      ),
                    )}
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
        <footer className="composer-area">
          {error && (
            <div className="error" role="alert">
              {error}
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                ×
              </button>
            </div>
          )}
          <form onSubmit={ask}>
            <label className="sr-only" htmlFor="question">
              Ask about your PDFs
            </label>
            <textarea
              id="question"
              placeholder="What would you like to understand?"
              value={question}
              maxLength={4000}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={streaming}
            />
            <div className="composer-actions">
              <small>
                {config?.provider_mode !== "live"
                  ? "Fixture demo · no API calls or quality claims"
                  : "Answers use only your selected PDFs"}
              </small>
              {streaming ? (
                <button
                  type="button"
                  onClick={() => controller.current?.abort()}
                >
                  Stop
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={
                    !permitted || !readySelected.length || !question.trim()
                  }
                >
                  Ask ↗
                </button>
              )}
            </div>
          </form>
          <p className="footnote">
            Always check the source. Retrieval threshold:{" "}
            {config?.threshold_label || "connecting"}.
          </p>
        </footer>
      </main>
      {target && (
        <Suspense
          fallback={
            <aside className="source-panel">Loading source viewer…</aside>
          }
        >
          <PdfViewer
            target={target}
            title={
              documents.find((d) => d.id === target.documentId)?.filename ||
              "Source document"
            }
            onClose={() => setTarget(null)}
          />
        </Suspense>
      )}
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
