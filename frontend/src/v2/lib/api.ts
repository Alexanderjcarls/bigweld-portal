import type { UIMessage } from "ai";

export const DEFAULT_CHAT_API_URL = "http://localhost:8886/chat";

export function getChatApiUrl(): string {
  return import.meta.env.VITE_BIGWELD_V2_CHAT_URL ?? DEFAULT_CHAT_API_URL;
}

export interface ChatRequestBody {
  id: string;
  messages: UIMessage[];
  trigger: "submit-message" | "regenerate-message";
  messageId?: string;
  conv_id: string;
  user_msg: string;
}

export function buildChatRequestBody(options: {
  chatId: string;
  conversationId: string;
  messages: UIMessage[];
  trigger: "submit-message" | "regenerate-message";
  messageId?: string;
  body?: Record<string, unknown>;
}): ChatRequestBody & Record<string, unknown> {
  return {
    ...options.body,
    id: options.chatId,
    messages: options.messages,
    trigger: options.trigger,
    messageId: options.messageId,
    conv_id: options.conversationId,
    user_msg: getLastUserText(options.messages),
  };
}

export function getLastUserText(messages: UIMessage[]): string {
  const userMessage = [...messages].reverse().find((message) => message.role === "user");
  if (!userMessage) return "";

  return userMessage.parts
    .map((part) => (part.type === "text" ? part.text : ""))
    .join("")
    .trim();
}
