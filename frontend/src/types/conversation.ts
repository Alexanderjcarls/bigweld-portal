export interface ConversationListItem {
  id: string;
  mtime: number;
  has_summary: boolean;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  toolCalls: { tool: string; input: unknown; output: string }[];
  ts: string;
  isStreaming: boolean;
}
