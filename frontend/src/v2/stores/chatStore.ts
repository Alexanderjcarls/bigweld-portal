import { create } from "zustand";

const STORAGE_KEY = "bigweld-v2-conversation-id";

interface ChatState {
  conversationId: string;
  lastSubmittedText: string;
  setConversationId: (conversationId: string) => void;
  setLastSubmittedText: (text: string) => void;
  resetConversation: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  conversationId: readConversationId(),
  lastSubmittedText: "",
  setConversationId: (conversationId) => {
    writeConversationId(conversationId);
    set({ conversationId });
  },
  setLastSubmittedText: (lastSubmittedText) => set({ lastSubmittedText }),
  resetConversation: () => {
    const conversationId = createConversationId();
    writeConversationId(conversationId);
    set({ conversationId, lastSubmittedText: "" });
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
