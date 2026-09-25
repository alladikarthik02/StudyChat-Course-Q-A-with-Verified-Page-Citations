import { useEffect, useRef, useState } from "react";
import { getDocument, GlobalWorkerOptions, TextLayer } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import "pdfjs-dist/web/pdf_viewer.css";
import { quoteSpan } from "./highlight";
import type { ViewerTarget } from "./types";

GlobalWorkerOptions.workerSrc = workerUrl;

export function PdfViewer({
  target,
  title,
  onClose,
}: {
  target: ViewerTarget;
  title: string;
  onClose: () => void;
}) {
  const stage = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState("Loading source page…");
  useEffect(() => {
    let cancelled = false;
    const holder = stage.current!;
    const canvas = document.createElement("canvas");
    canvas.setAttribute("aria-label", `PDF page ${target.page}`);
    const textContainer = document.createElement("div");
    textContainer.className = "textLayer";
    holder.replaceChildren(canvas, textContainer);
    setStatus("Loading source page…");
    const task = getDocument({
      url: `/api/documents/${encodeURIComponent(target.documentId)}/file`,
    });
    let render: { cancel: () => void; promise: Promise<unknown> } | undefined;
    let layer: TextLayer | undefined;
    (async () => {
      const pdf = await task.promise;
      const page = await pdf.getPage(target.page);
      if (cancelled) return;
      const scale = Math.min(
        1.2,
        Math.max(
          0.35,
          (holder.parentElement!.clientWidth - 36) /
            page.getViewport({ scale: 1 }).width,
        ),
      );
      const viewport = page.getViewport({ scale });
      holder.style.width = `${viewport.width}px`;
      holder.style.height = `${viewport.height}px`;
      holder.style.setProperty("--scale-factor", String(scale));
      holder.style.setProperty(
        "--total-scale-factor",
        String(scale * viewport.userUnit),
      );
      holder.style.setProperty("--scale-round-x", "1px");
      holder.style.setProperty("--scale-round-y", "1px");
      canvas.width = Math.ceil(viewport.width);
      canvas.height = Math.ceil(viewport.height);
      render = page.render({ canvas, viewport });
      await render.promise;
      if (cancelled) return;
      layer = new TextLayer({
        textContentSource: await page.getTextContent(),
        container: textContainer,
        viewport,
      });
      await layer.render();
      if (cancelled) return;
      const divs = layer.textDivs;
      const raw = divs.map((div) => div.textContent || "").join("\n");
      const span = target.ambiguous ? null : quoteSpan(raw, target.quote);
      let highlighted = false,
        cursor = 0;
      const origin = holder.getBoundingClientRect();
      if (span)
        for (const div of divs) {
          const length = div.textContent?.length || 0;
          const from = Math.max(0, span[0] - cursor),
            to = Math.min(length, span[1] - cursor);
          if (from < to && div.firstChild?.nodeType === Node.TEXT_NODE) {
            const range = document.createRange();
            range.setStart(div.firstChild, from);
            range.setEnd(div.firstChild, to);
            for (const rect of range.getClientRects()) {
              if (!rect.width || !rect.height) continue;
              const highlight = document.createElement("div");
              highlight.className = "quote-highlight";
              Object.assign(highlight.style, {
                left: `${rect.left - origin.left}px`,
                top: `${rect.top - origin.top}px`,
                width: `${rect.width}px`,
                height: `${rect.height}px`,
              });
              holder.append(highlight);
              highlighted = true;
            }
          }
          cursor += length + 1;
        }
      setStatus(
        highlighted
          ? "Quote highlighted on this page"
          : "Highlight unavailable or ambiguous. Read the quote below.",
      );
    })().catch(() => {
      if (!cancelled)
        setStatus(
          "Could not display this PDF. The source may have been deleted.",
        );
    });
    return () => {
      cancelled = true;
      render?.cancel();
      layer?.cancel();
      void task.destroy();
    };
  }, [target]);
  return (
    <aside className="source-panel" aria-label="Source viewer">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">SOURCE CHECK</p>
          <h2>{title}</h2>
        </div>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="Close source viewer"
        >
          ×
        </button>
      </div>
      <p className="page-label">Physical page {target.page}</p>
      <p role="status" className="viewer-status">
        {status}
      </p>
      <div className="pdf-scroll">
        <div className="pdf-stage" ref={stage} />
      </div>
      <blockquote>{target.quote}</blockquote>
    </aside>
  );
}
