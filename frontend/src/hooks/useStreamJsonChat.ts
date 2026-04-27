import { useCallback } from "react";
import { useChatStore } from "@/stores/chatStore";
import { useResumeStore } from "@/stores/resumeStore";
import { createConversation, takeTurnStream } from "@/lib/api";
import { ndjsonReader } from "@/lib/ndjson";
import type { StreamJsonEvent } from "@/types/stream";

export function useStreamJsonChat() {
  const {
    conversationId, setConversationId, startUserTurn,
    appendAssistantToken, appendToolCall, finalizeAssistantTurn, setStreaming,
  } = useChatStore();
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

    let pendingToolName: string | null = null;
    let pendingToolInput = "";

    try {
      const response = await takeTurnStream(convId, message);
      for await (const ev of ndjsonReader<StreamJsonEvent>(response.body!)) {
        if (ev.type === "stream_event") {
          const sub = ev.event;
          if (sub.type === "content_block_start" && sub.content_block?.type === "tool_use") {
            pendingToolName = sub.content_block.name ?? "tool";
            pendingToolInput = "";
          } else if (sub.type === "content_block_delta") {
            if (sub.delta.type === "text_delta" && sub.delta.text) {
              appendAssistantToken(assistantMsgId, sub.delta.text);
            } else if (sub.delta.type === "input_json_delta" && sub.delta.partial_json) {
              pendingToolInput += sub.delta.partial_json;
            }
          }
        } else if (ev.type === "user" && pendingToolName) {
          // tool_result echo
          const block = ev.message.content[0];
          if (block?.type === "tool_result") {
            appendToolCall(
              assistantMsgId, pendingToolName,
              tryParseJson(pendingToolInput), block.output ?? "",
            );
            pendingToolName = null;
            pendingToolInput = "";
          }
        } else if (ev.type === "result") {
          finalizeAssistantTurn(assistantMsgId);
        } else if (ev.type === "system" && ev.is_error) {
          appendAssistantToken(assistantMsgId, `\n\n[error] ${ev.error ?? "unknown"}`);
          finalizeAssistantTurn(assistantMsgId);
        }
      }
    } catch {
      setLastFailedMessage(message);
      appendAssistantToken(assistantMsgId, "\n\n[connection lost — click Resume]");
      finalizeAssistantTurn(assistantMsgId);
      setStreaming(false);
    } finally {
      setStreaming(false);
    }
  }, [conversationId, setConversationId, startUserTurn, appendAssistantToken,
      appendToolCall, finalizeAssistantTurn, setStreaming, setLastFailedMessage]);

  return { sendTurn };
}

function tryParseJson(s: string): unknown {
  try { return JSON.parse(s); } catch { return s; }
}
