export type StreamJsonEvent =
  | { type: "system"; subtype?: string; session_id?: string; is_error?: boolean; error?: string }
  | { type: "stream_event"; event: StreamSubEvent }
  | { type: "assistant"; message: { content: ContentBlock[] } }
  | { type: "user"; message: { content: ContentBlock[] } }
  | { type: "result"; cost_usd?: number; duration_ms?: number; session_id?: string };

export type StreamSubEvent =
  | { type: "message_start" }
  | { type: "content_block_start"; content_block: { type: "text" | "tool_use"; name?: string } }
  | { type: "content_block_delta"; delta: { type: "text_delta" | "input_json_delta" | "thinking_delta"; text?: string; partial_json?: string } }
  | { type: "content_block_stop" }
  | { type: "message_delta"; delta: Record<string, unknown> }
  | { type: "message_stop" };

export interface ContentBlock {
  type: "text" | "tool_use" | "tool_result";
  text?: string;
  name?: string;
  input?: Record<string, unknown>;
  output?: string;
}
