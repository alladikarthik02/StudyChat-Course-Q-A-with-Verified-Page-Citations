export type DocumentInfo = {
  id: string;
  filename: string;
  state: string;
  page_count: number;
  error_code: string | null;
};
export type Citation = {
  status: "exact" | "approximate" | "removed";
  reason: string | null;
  document_id: string | null;
  matched_text: string | null;
  ambiguous: boolean;
  citation: { page: number; quote: string; raw: string };
  score: number | null;
};
export type Verification = {
  text: string;
  citations: Citation[];
  has_verified_citations: boolean;
};
export type ViewerTarget = {
  documentId: string;
  page: number;
  quote: string;
  ambiguous: boolean;
};
export type StreamEvent = {
  event: string;
  request_id: string;
  seq: number;
  text?: string;
  result?: Verification;
  outcome?: string;
  code?: string;
  reason?: string;
};
