import { create } from "zustand";
import type { UIMessage } from "ai";

const STORAGE_KEY = "bigweld-v2-conversation-id";

interface ChatState {
  conversationId: string;
  lastSubmittedText: string;
  messageCount: number;
  hydratedConversationId: string | null;
  hydratedMessages: UIMessage[] | null;
  setConversationId: (conversationId: string) => void;
  setLastSubmittedText: (text: string) => void;
  setMessageCount: (messageCount: number) => void;
  hydrateConversation: (conversationId: string, messages: UIMessage[]) => void;
  clearHydratedConversation: () => void;
  resetConversation: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  conversationId: readConversationId(),
  lastSubmittedText: "",
  messageCount: 0,
  hydratedConversationId: null,
  hydratedMessages: null,
  setConversationId: (conversationId) => {
    writeConversationId(conversationId);
    set({ conversationId });
  },
  setLastSubmittedText: (lastSubmittedText) => set({ lastSubmittedText }),
  setMessageCount: (messageCount) => set({ messageCount }),
  hydrateConversation: (conversationId, messages) =>
    set({
      conversationId,
      hydratedConversationId: conversationId,
      hydratedMessages: messages,
      messageCount: messages.length,
    }),
  clearHydratedConversation: () =>
    set({ hydratedConversationId: null, hydratedMessages: null }),
  resetConversation: () => {
    const conversationId = createConversationId();
    writeConversationId(conversationId);
    set({
      conversationId,
      lastSubmittedText: "",
      messageCount: 0,
      hydratedConversationId: null,
      hydratedMessages: null,
    });
  },
}));

function readConversationId(): string {
  if (typeof window === "undefined") return createConversationId();

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) return stored;
  } catch {
    /* localStorage unavailable */
  }

  const conversationId = createConversationId();
  writeConversationId(conversationId);
  return conversationId;
}

function writeConversationId(conversationId: string): void {
  if (typeof window === "undefined") return;

  try {
    window.localStorage.setItem(STORAGE_KEY, conversationId);
  } catch {
    /* localStorage unavailable */
  }
}

function createConversationId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `v2-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
