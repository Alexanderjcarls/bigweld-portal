import { create } from "zustand";
import type { Message } from "@/types/conversation";

interface ChatState {
  conversationId: string | null;
  messages: Message[];
  inputDraft: string;
  attachedFiles: { name: string; size: number; data: string }[];
  isStreaming: boolean;

  setConversationId: (id: string | null) => void;
  loadMessages: (msgs: Message[]) => void;
  startUserTurn: (content: string) => string;
  appendAssistantToken: (id: string, token: string) => void;
  finalizeAssistantTurn: (id: string) => void;
  appendToolCall: (msgId: string, tool: string, input: unknown, output: string) => void;
  setInputDraft: (s: string) => void;
  attachFile: (f: { name: string; size: number; data: string }) => void;
  clearAttachments: () => void;
  setStreaming: (b: boolean) => void;
  reset: () => void;
}

let _id = 0;
const newId = () => `msg-${++_id}-${Date.now()}`;

export const useChatStore = create<ChatState>((set, get) => ({
  conversationId: null,
  messages: [],
  inputDraft: "",
  attachedFiles: [],
  isStreaming: false,

  setConversationId: (id) => set({ conversationId: id }),
  loadMessages: (msgs) => set({ messages: msgs }),
  startUserTurn: (content) => {
    const userMsg: Message = {
      id: newId(),
      role: "user",
      content,
      toolCalls: [],
      ts: new Date().toISOString(),
      isStreaming: false,
    };
    const assistantMsg: Message = {
      id: newId(),
      role: "assistant",
      content: "",
      toolCalls: [],
      ts: new Date().toISOString(),
      isStreaming: true,
    };
    set({ messages: [...get().messages, userMsg, assistantMsg] });
    return assistantMsg.id;
  },
  appendAssistantToken: (id, token) => set({
    messages: get().messages.map(m =>
      m.id === id ? { ...m, content: m.content + token } : m
    ),
  }),
  finalizeAssistantTurn: (id) => set({
    messages: get().messages.map(m =>
      m.id === id ? { ...m, isStreaming: false } : m
    ),
    isStreaming: false,
  }),
  appendToolCall: (msgId, tool, input, output) => set({
    messages: get().messages.map(m =>
      m.id === msgId
        ? { ...m, toolCalls: [...m.toolCalls, { tool, input, output }] }
        : m
    ),
  }),
  setInputDraft: (s) => set({ inputDraft: s }),
  attachFile: (f) => set({ attachedFiles: [...get().attachedFiles, f] }),
  clearAttachments: () => set({ attachedFiles: [] }),
  setStreaming: (b) => set({ isStreaming: b }),
  reset: () => set({
    conversationId: null,
    messages: [],
    inputDraft: "",
    attachedFiles: [],
    isStreaming: false,
  }),
}));
