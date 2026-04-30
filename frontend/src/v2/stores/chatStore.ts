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
  // crypto.randomUUID() is only available in secure contexts (HTTPS or
  // localhost). Over plain HTTP from a remote IP (e.g. LAN access to
  // staging at http://192.168.0.30:8886) it's undefined, so we fall through
  // to a manual UUIDv4 builder that uses crypto.getRandomValues (which
  // works regardless of secure-context status).
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    try {
      return crypto.randomUUID();
    } catch {
      /* fall through to manual UUIDv4 */
    }
  }

  return manualUuidV4();
}

function manualUuidV4(): string {
  // RFC 4122 §4.4 UUIDv4. Backend (bigweld_v2.conversations.id) is a UUID
  // PRIMARY KEY column; the previous fallback ("v2-{timestamp}-{rand}") was
  // rejected by Pydantic's UUID validator on the /chat endpoint.
  const bytes = new Uint8Array(16);
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < 16; i += 1) {
      bytes[i] = Math.floor(Math.random() * 256);
    }
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40; // version 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant 10xx
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20, 32)}`;
}
