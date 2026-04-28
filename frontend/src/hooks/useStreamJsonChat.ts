import { useCallback } from "react";
import { useChatStore } from "@/stores/chatStore";
import { useResumeStore } from "@/stores/resumeStore";
import { createConversation, takeTurnStream } from "@/lib/api";
import { ndjsonReader } from "@/lib/ndjson";
import type { ContentBlock, StreamJsonEvent } from "@/types/stream";

export function useStreamJsonChat() {
  const conversationId = useChatStore(s => s.conversationId);
  const setConversationId = useChatStore(s => s.setConversationId);
  const startUserTurn = useChatStore(s => s.startUserTurn);
  const beginAssistantBlock = useChatStore(s => s.beginAssistantBlock);
  const appendToCurrentTextBlock = useChatStore(s => s.appendToCurrentTextBlock);
  const appendToCurrentThinkingBlock = useChatStore(s => s.appendToCurrentThinkingBlock);
  const appendToolUseInput = useChatStore(s => s.appendToolUseInput);
  const finalizeToolUse = useChatStore(s => s.finalizeToolUse);
  const finalizeAssistantTurn = useChatStore(s => s.finalizeAssistantTurn);
  const setStreaming = useChatStore(s => s.setStreaming);
  const setLastFailedMessage = useResumeStore(s => s.setLastFailedMessage);

  const sendTurn = useCallback(async (message: string) => {
    let convId = conversationId;
    if (!convId) {
      const created = await createConversation();
      convId = created.conv_id;
      setConversationId(convId);
    }
    const assistantMsgId = startUserTurn(message);
    setStreaming(true);

    let currentToolUseId: string | null = null;

    try {
      const response = await takeTurnStream(convId, message);
      for await (const ev of ndjsonReader<StreamJsonEvent>(response.body!)) {
        if (ev.type === "stream_event") {
          const sub = ev.event;
          if (sub.type === "content_block_start") {
            if (sub.content_block?.type === "text") {
              beginAssistantBlock(assistantMsgId, { kind: "text", text: "" });
            } else if (sub.content_block?.type === "tool_use") {
              currentToolUseId = sub.content_block.id ?? crypto.randomUUID();
              beginAssistantBlock(assistantMsgId, {
                kind: "tool_use",
                id: currentToolUseId,
                name: sub.content_block.name ?? "tool",
                input: sub.content_block.input ?? {},
                isStreaming: true,
              });
            } else if (sub.content_block?.type === "thinking") {
              beginAssistantBlock(assistantMsgId, { kind: "thinking", text: "" });
            }
          } else if (sub.type === "content_block_delta") {
            if (sub.delta.type === "text_delta" && sub.delta.text) {
              appendToCurrentTextBlock(assistantMsgId, sub.delta.text);
            } else if (
              sub.delta.type === "input_json_delta" &&
              sub.delta.partial_json &&
              currentToolUseId
            ) {
              appendToolUseInput(assistantMsgId, currentToolUseId, sub.delta.partial_json);
            } else if (sub.delta.type === "thinking_delta") {
              const thinking = sub.delta.text ?? sub.delta.thinking;
              if (thinking) appendToCurrentThinkingBlock(assistantMsgId, thinking);
            }
          }
        } else if (ev.type === "user") {
          for (const block of ev.message.content) {
            if (block?.type === "tool_result" && block.tool_use_id) {
              const result = toolResultToText(block);
              finalizeToolUse(
                assistantMsgId,
                block.tool_use_id,
                result.output,
                result.error,
              );
              if (block.tool_use_id === currentToolUseId) {
                currentToolUseId = null;
              }
            }
          }
        } else if (ev.type === "result") {
          finalizeAssistantTurn(assistantMsgId);
        } else if (ev.type === "system" && ev.is_error) {
          appendToCurrentTextBlock(assistantMsgId, `\n\n[error] ${ev.error ?? "unknown"}`);
          finalizeAssistantTurn(assistantMsgId);
        }
      }
    } catch {
      setLastFailedMessage(message);
      appendToCurrentTextBlock(assistantMsgId, "\n\n[connection lost - click Resume]");
      finalizeAssistantTurn(assistantMsgId);
      setStreaming(false);
    } finally {
      setStreaming(false);
    }
  }, [
    conversationId,
    setConversationId,
    startUserTurn,
    beginAssistantBlock,
    appendToCurrentTextBlock,
    appendToCurrentThinkingBlock,
    appendToolUseInput,
    finalizeToolUse,
    finalizeAssistantTurn,
    setStreaming,
    setLastFailedMessage,
  ]);

  return { sendTurn };
}

function toolResultToText(block: ContentBlock): { output: string; error?: string } {
  const raw = block.output ?? block.content ?? "";
  const output = Array.isArray(raw)
    ? raw.map(item => typeof item?.text === "string" ? item.text : "").join("")
    : String(raw);
  return {
    output,
    error: block.is_error ? output || "tool returned an error" : undefined,
  };
}
