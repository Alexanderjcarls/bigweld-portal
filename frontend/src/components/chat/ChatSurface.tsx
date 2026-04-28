import { useEffect } from "react";
import { MessageThread } from "./MessageThread";
import { ChatInput } from "./ChatInput";
import { ChatInputBoundary } from "./ChatInputBoundary";
import { ContextBars } from "./ContextBars";
import { ResumeBanner } from "./ResumeBanner";
import { SessionControls } from "./SessionControls";
import { TextareaFallback } from "./TextareaFallback";
import { useChatStore } from "@/stores/chatStore";
import { getConversation } from "@/lib/api";
import type { Message, MessageBlock } from "@/types/conversation";

let _hydrateId = 0;
const newMessageId = () => `hyd-${++_hydrateId}-${Date.now()}`;

export function eventsToMessages(events: Record<string, unknown>[]): Message[] {
  const out: Message[] = [];
  for (const ev of events) {
    const type = ev.type;
    if (type === "user" && typeof ev.content === "string") {
      out.push({
        id: newMessageId(),
        role: "user",
        blocks: [{ kind: "text", text: ev.content }],
        ts: typeof ev.ts === "string" ? ev.ts : new Date().toISOString(),
        isStreaming: false,
      });
    } else if (type === "assistant") {
      const blocks = assistantBlocksFromEvent(ev);
      if (blocks.length > 0) {
        const assistant = ensureCurrentAssistant(out, ev);
        assistant.blocks = shouldReplaceToolPlaceholder(assistant, ev)
          ? blocks
          : [...assistant.blocks, ...blocks];
      }
    } else if (type === "tool_use_result") {
      ensureCurrentAssistant(out, ev).blocks.push(toolResultBlockFromEvent(ev));
    }
  }
  return out;
}

export function ChatSurface() {
  const conversationId = useChatStore(s => s.conversationId);
  const messagesLength = useChatStore(s => s.messages.length);
  const loadMessages = useChatStore(s => s.loadMessages);
  const setConversationId = useChatStore(s => s.setConversationId);

  useEffect(() => {
    if (!conversationId || messagesLength > 0) return;
    let cancelled = false;
    getConversation(conversationId)
      .then(data => {
        if (cancelled) return;
        const events = (data?.events ?? []) as Record<string, unknown>[];
        loadMessages(eventsToMessages(events));
      })
      .catch(() => {
        // Conversation gone (deleted on disk?). Clear the stale id.
        if (!cancelled) setConversationId(null);
      });
    return () => {
      cancelled = true;
    };
  }, [conversationId, messagesLength, loadMessages, setConversationId]);

  return (
    <div className="flex h-full flex-col border-r border-border bg-card">
      <MessageThread />
      <div className="border-t border-border bg-card/50">
        <ResumeBanner />
        <ChatInputBoundary fallback={<TextareaFallback />}>
          <ChatInput />
        </ChatInputBoundary>
        <div className="flex justify-between items-center px-4 pb-3">
          <ContextBars />
          <SessionControls />
        </div>
      </div>
    </div>
  );
}

function shouldReplaceToolPlaceholder(
  assistant: Message,
  ev: Record<string, unknown>,
): boolean {
  return Array.isArray(ev.blocks)
    && assistant.blocks.length > 0
    && assistant.blocks.every(block => block.kind === "tool_use");
}

function ensureCurrentAssistant(out: Message[], ev: Record<string, unknown>): Message {
  const last = out[out.length - 1];
  if (last?.role === "assistant") return last;

  const assistant: Message = {
    id: newMessageId(),
    role: "assistant",
    blocks: [],
    ts: typeof ev.ts === "string" ? ev.ts : new Date().toISOString(),
    isStreaming: false,
  };
  out.push(assistant);
  return assistant;
}

function assistantBlocksFromEvent(ev: Record<string, unknown>): MessageBlock[] {
  const blocks: MessageBlock[] = [];
  if (Array.isArray(ev.blocks)) {
    blocks.push(...ev.blocks.flatMap(blockFromUnknown));
  }

  if (isRecord(ev.message) && Array.isArray(ev.message.content)) {
    blocks.push(...ev.message.content.flatMap(blockFromUnknown));
  }

  if (blocks.length > 0) return blocks;
  if (typeof ev.content === "string" && ev.content.trim() !== "") {
    return [{ kind: "text", text: ev.content }];
  }
  return [];
}

function blockFromUnknown(value: unknown): MessageBlock[] {
  if (!isRecord(value)) return [];
  if (value.kind === "text" && typeof value.text === "string") {
    return [{ kind: "text", text: value.text }];
  }
  if (value.kind === "thinking" && typeof value.text === "string") {
    return [{ kind: "thinking", text: value.text }];
  }
  if (value.kind === "tool_use" && typeof value.id === "string") {
    return [{
      kind: "tool_use",
      id: value.id,
      name: typeof value.name === "string" ? value.name : "tool",
      input: toRecord(value.input),
      output: typeof value.output === "string" ? value.output : undefined,
      error: typeof value.error === "string" ? value.error : undefined,
      isStreaming: false,
    }];
  }

  if (value.type === "text" && typeof value.text === "string") {
    return [{ kind: "text", text: value.text }];
  }
  if (value.type === "thinking" && typeof value.text === "string") {
    return [{ kind: "thinking", text: value.text }];
  }
  if (value.type === "tool_use") {
    return [{
      kind: "tool_use",
      id: typeof value.id === "string" ? value.id : newMessageId(),
      name: typeof value.name === "string" ? value.name : "tool",
      input: toRecord(value.input),
      isStreaming: false,
    }];
  }
  return [];
}

function toolResultBlockFromEvent(ev: Record<string, unknown>): MessageBlock {
  const output = ev.output;
  const outputRecord = isRecord(output) ? output : null;
  const stdout = outputRecord?.stdout;
  const stderr = outputRecord?.stderr;
  const outputText = typeof output === "string"
    ? output
    : stdout !== undefined
      ? String(stdout)
      : stringifyUnknown(output);
  const errorText = typeof stderr === "string" && stderr.trim() !== ""
    ? stderr
    : outputRecord?.is_error
      ? outputText || "tool returned an error"
      : undefined;

  return {
    kind: "tool_use",
    id: typeof ev.tool_use_id === "string" ? ev.tool_use_id : newMessageId(),
    name: typeof ev.tool === "string" ? ev.tool : "tool",
    input: toRecord(ev.input),
    output: outputText,
    error: errorText,
    isStreaming: false,
  };
}

function toRecord(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {};
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function stringifyUnknown(value: unknown): string {
  if (value === undefined || value === null) return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}
