export function normalizeMap(source: string) {
  let text = "";
  const starts: number[] = [],
    ends: number[] = [];
  for (const { segment, index } of new Intl.Segmenter(undefined, {
    granularity: "grapheme",
  }).segment(source)) {
    const normalized = segment.normalize("NFKC");
    text += normalized;
    for (let i = 0; i < normalized.length; i++) {
      starts.push(index);
      ends.push(index + segment.length);
    }
  }
  if (text !== source.normalize("NFKC"))
    throw new Error("Text mapping unavailable");
  const dropped = new Set<number>();
  for (const match of text.matchAll(/(?<=\p{L})-\s*\n\s*(?=\p{L})/gu)) {
    for (let i = match.index; i < match.index + match[0].length; i++)
      dropped.add(i);
  }
  let clean = "";
  const cleanStarts: number[] = [],
    cleanEnds: number[] = [];
  for (let i = 0; i < text.length; i++) {
    if (dropped.has(i)) continue;
    const char = text[i];
    if (/\s/u.test(char)) {
      if (!clean) continue;
      if (clean.endsWith(" ")) {
        cleanEnds[cleanEnds.length - 1] = ends[i];
        continue;
      }
      clean += " ";
    } else clean += char;
    cleanStarts.push(starts[i]);
    cleanEnds.push(ends[i]);
  }
  if (clean.endsWith(" ")) {
    clean = clean.slice(0, -1);
    cleanStarts.pop();
    cleanEnds.pop();
  }
  return { text: clean, starts: cleanStarts, ends: cleanEnds };
}

export function quoteSpan(
  source: string,
  quote: string,
): [number, number] | null {
  const mapped = normalizeMap(source),
    needle = normalizeMap(quote).text;
  if (!needle) return null;
  const first = mapped.text.indexOf(needle);
  if (first < 0 || mapped.text.indexOf(needle, first + 1) >= 0) return null;
  return [mapped.starts[first], mapped.ends[first + needle.length - 1]];
}
