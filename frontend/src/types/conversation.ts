export interface ConversationListItem {
  id: string;
  mtime: number;
  has_summary: boolean;
}

export type MessageBlock =
  | { kind: "text"; text: string }
  | {
      kind: "tool_use";
      id: string;
      name: string;
      input: Record<string, unknown>;
      output?: string;
      error?: string;
      isStreaming?: boolean;
    }
  | { kind: "thinking"; text: string };

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  blocks: MessageBlock[];
  ts: string;
  isStreaming: boolean;
}
