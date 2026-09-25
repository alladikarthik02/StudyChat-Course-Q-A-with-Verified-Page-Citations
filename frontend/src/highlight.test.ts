import { expect, test } from "vitest";
import { normalizeMap, quoteSpan } from "./highlight";
test("ligatures, combining marks and dehyphenation map back to UTF-16 offsets", () => {
  const source = "👩‍💻 ﬁrst cafe\u0301 inter-\nnational";
  const span = quoteSpan(source, "first café international")!;
  expect(source.slice(...span)).toBe("ﬁrst cafe\u0301 inter-\nnational");
  expect(normalizeMap("가").text).toBe("가");
});
test("missing or ambiguous matches never highlight a guess", () => {
  expect(quoteSpan("same same", "same")).toBeNull();
  expect(quoteSpan("different", "quote")).toBeNull();
  expect(quoteSpan("text", "")).toBeNull();
});
