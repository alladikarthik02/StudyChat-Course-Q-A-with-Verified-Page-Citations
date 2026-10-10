import { memo } from "react";
import {
  PlannedMarkdown,
  useStreamSnapshot,
  type MarkdownController,
} from "@alladikarthik/stream-md";

// A message subscribes to frame-batched output without rerendering the whole chat.
export const AnswerMarkdown = memo(function AnswerMarkdown({
  renderer,
}: {
  renderer: MarkdownController;
}) {
  const snapshot = useStreamSnapshot(renderer);
  return (
    <div className="answer-text">
      <PlannedMarkdown plan={snapshot.plan} />
    </div>
  );
});
