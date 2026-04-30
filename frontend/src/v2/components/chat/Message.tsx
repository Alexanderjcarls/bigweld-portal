import type { ReactNode } from "react";
import {
  Message as AIMessage,
  MessageContent,
} from "@/v2/components/ai-elements/message";
import { Response } from "@/v2/components/ai-elements/response";

interface ChatMessageProps {
  from: "system" | "user" | "assistant";
  children: ReactNode;
}

export function ChatMessage({ from, children }: ChatMessageProps) {
  return (
    <AIMessage from={from}>
      <MessageContent>{children}</MessageContent>
    </AIMessage>
  );
}

interface TextMessageProps {
  from: "system" | "user" | "assistant";
  text: string;
}

export function TextMessage({ from, text }: TextMessageProps) {
  if (!text.trim()) return null;

  return (
    <ChatMessage from={from}>
      <Response>{text}</Response>
    </ChatMessage>
  );
}
