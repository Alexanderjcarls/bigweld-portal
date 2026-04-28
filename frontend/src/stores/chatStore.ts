import { create } from "zustand";
import type { Message, MessageBlock } from "@/types/conversation";

export type AttachedFile =
  | { kind: "text"; name: string; size: number; data: string }
  | { kind: "binary"; name: string; size: number; path: string };

interface ChatState {
  conversationId: string | null;
  messages: Message[];
  inputDraft: string;
  attachedFiles: AttachedFile[];
  isStreaming: boolean;

  setConversationId: (id: string | null) => void;
  loadMessages: (msgs: Message[]) => void;
  startUserTurn: (content: string) => string;
  beginAssistantBlock: (msgId: string, block: MessageBlock) => void;
  appendToCurrentTextBlock: (msgId: string, delta: string) => void;
  appendToCurrentThinkingBlock: (msgId: string, delta: string) => void;
  appendToolUseInput: (msgId: string, toolUseId: string, jsonDelta: string) => void;
  finalizeToolUse: (msgId: string, toolUseId: string, output: string, error?: string) => void;
  finalizeAssistantTurn: (id: string) => void;
  setInputDraft: (s: string) => void;
  attachFile: (f: AttachedFile) => void;
  clearAttachments: () => void;
  setStreaming: (b: boolean) => void;
  reset: () => void;
}

let _id = 0;
const newId = () => `msg-${++_id}-${Date.now()}`;

const CONV_KEY = "bigweld-conversation-id";
const toolInputBuffers = new Map<string, string>();
const toolBufferKey = (msgId: string, toolUseId: string) => `${msgId}:${toolUseId}`;

const initialConvId = (() => {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(CONV_KEY);
  } catch {
    return null;
  }
})();

export const useChatStore = create<ChatState>((set, get) => ({
  conversationId: initialConvId,
  messages: [],
  inputDraft: "",
  attachedFiles: [],
  isStreaming: false,

  setConversationId: (id) => {
    set({ conversationId: id });
    try {
      if (id) localStorage.setItem(CONV_KEY, id);
      else localStorage.removeItem(CONV_KEY);
    } catch {
      /* localStorage unavailable */
    }
  },
  loadMessages: (msgs) => {
    toolInputBuffers.clear();
    set({ messages: msgs });
  },
  startUserTurn: (content) => {
    const userMsg: Message = {
      id: newId(),
      role: "user",
      blocks: [{ kind: "text", text: content }],
      ts: new Date().toISOString(),
      isStreaming: false,
    };
    const assistantMsg: Message = {
      id: newId(),
      role: "assistant",
      blocks: [],
      ts: new Date().toISOString(),
      isStreaming: true,
    };
    set({ messages: [...get().messages, userMsg, assistantMsg] });
    return assistantMsg.id;
  },
  beginAssistantBlock: (msgId, block) => {
    if (block.kind === "tool_use") {
      toolInputBuffers.delete(toolBufferKey(msgId, block.id));
    }
    set({
      messages: get().messages.map(m =>
        m.id === msgId ? { ...m, blocks: [...m.blocks, block] } : m
      ),
    });
  },
  appendToCurrentTextBlock: (id, delta) => set({
    messages: get().messages.map(m =>
      m.id === id ? { ...m, blocks: appendTextBlock(m.blocks, delta) } : m
    ),
  }),
  appendToCurrentThinkingBlock: (id, delta) => set({
    messages: get().messages.map(m =>
      m.id === id ? { ...m, blocks: appendThinkingBlock(m.blocks, delta) } : m
    ),
  }),
  appendToolUseInput: (msgId, toolUseId, jsonDelta) => {
    const key = toolBufferKey(msgId, toolUseId);
    toolInputBuffers.set(key, (toolInputBuffers.get(key) ?? "") + jsonDelta);
  },
  finalizeToolUse: (msgId, toolUseId, output, error) => {
    const key = toolBufferKey(msgId, toolUseId);
    const input = parseToolInput(toolInputBuffers.get(key) ?? "");
    toolInputBuffers.delete(key);
    set({
      messages: get().messages.map(m =>
        m.id === msgId
          ? { ...m, blocks: finalizeToolBlock(m.blocks, toolUseId, input, output, error) }
          : m
      ),
    });
  },
  finalizeAssistantTurn: (id) => set({
    messages: get().messages.map(m =>
      m.id === id ? { ...m, isStreaming: false } : m
    ),
    isStreaming: false,
  }),
  setInputDraft: (s) => set({ inputDraft: s }),
  attachFile: (f) => set({ attachedFiles: [...get().attachedFiles, f] }),
  clearAttachments: () => set({ attachedFiles: [] }),
  setStreaming: (b) => set({ isStreaming: b }),
  reset: () => {
    try {
      localStorage.removeItem(CONV_KEY);
    } catch {
      /* ignore */
    }
    toolInputBuffers.clear();
    set({
      conversationId: null,
      messages: [],
      inputDraft: "",
      attachedFiles: [],
      isStreaming: false,
    });
  },
}));

function appendTextBlock(blocks: MessageBlock[], delta: string): MessageBlock[] {
  const next = [...blocks];
  const last = next[next.length - 1];
  if (last?.kind === "text") {
    next[next.length - 1] = { ...last, text: last.text + delta };
  } else {
    next.push({ kind: "text", text: delta });
  }
  return next;
}

function appendThinkingBlock(blocks: MessageBlock[], delta: string): MessageBlock[] {
  const next = [...blocks];
  const last = next[next.length - 1];
  if (last?.kind === "thinking") {
    next[next.length - 1] = { ...last, text: last.text + delta };
  } else {
    next.push({ kind: "thinking", text: delta });
  }
  return next;
}

function parseToolInput(raw: string): Record<string, unknown> | null {
  if (!raw.trim()) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    /* fall through */
  }
  return { raw };
}

function finalizeToolBlock(
  blocks: MessageBlock[],
  toolUseId: string,
  input: Record<string, unknown> | null,
  output: string,
  error?: string,
): MessageBlock[] {
  let matched = false;
  const next = blocks.map(block => {
    if (block.kind !== "tool_use" || block.id !== toolUseId) return block;
    matched = true;
    return {
      ...block,
      input: input ?? block.input,
      output,
      error,
      isStreaming: false,
    };
  });

  if (!matched) {
    next.push({
      kind: "tool_use",
      id: toolUseId,
      name: "tool",
      input: input ?? {},
      output,
      error,
      isStreaming: false,
    });
  }
  return next;
}
