import {
  getToolName,
  isToolUIPart,
  type UIDataTypes,
  type UIMessage,
  type UIMessagePart,
  type UITools,
} from "ai";
import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/v2/components/ai-elements/conversation";
import {
  PromptInput,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputToolbar,
  PromptInputTools,
} from "@/v2/components/ai-elements/prompt-input";
import { useChat } from "@/v2/hooks/useChat";
import { useChatStore } from "@/v2/stores/chatStore";
import { TextMessage } from "@/v2/components/chat/Message";
import { Reasoning } from "@/v2/components/chat/Reasoning";
import { ToolCall } from "@/v2/components/chat/ToolCall";
import {
  activityTagFromEvent,
  activityTagFromToolCall,
  BusyIndicator,
} from "@/v2/components/chat/BusyIndicator";
import { dispatchContextStatsChatEvent } from "@/v2/hooks/useContextStats";

export function ChatSurface() {
  const [input, setInput] = useState("");
  const [activityTag, setActivityTag] = useState("working");
  const conversationId = useChatStore((state) => state.conversationId);
  const setLastSubmittedText = useChatStore((state) => state.setLastSubmittedText);
  const setMessageCount = useChatStore((state) => state.setMessageCount);
  const hydratedConversationId = useChatStore((state) => state.hydratedConversationId);
  const hydratedMessages = useChatStore((state) => state.hydratedMessages);
  const clearHydratedConversation = useChatStore((state) => state.clearHydratedConversation);
  const { messages, setMessages, sendMessage, status, error, stop } = useChat({
    onToolCall: ({ toolCall }) => {
      setActivityTag(activityTagFromToolCall(toolCall));
    },
    onFinish: () => {
      dispatchContextStatsChatEvent();
      setActivityTag("working");
    },
  });
  const isBusy = status === "submitted" || status === "streaming";
  const busyTag = latestActivityTag(messages) ?? activityTag;

  useEffect(() => {
    if (hydratedConversationId !== conversationId || !hydratedMessages) return;

    setMessages(hydratedMessages);
    clearHydratedConversation();
  }, [
    clearHydratedConversation,
    conversationId,
    hydratedConversationId,
    hydratedMessages,
    setMessages,
  ]);

  useEffect(() => {
    setMessageCount(messages.length);
    dispatchContextStatsChatEvent();
  }, [messages.length, setMessageCount]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (status === "streaming") {
      stop();
      return;
    }

    const text = input.trim();
    if (!text || status === "submitted") return;

    setLastSubmittedText(text);
    setInput("");
    sendMessage({ text }).catch((sendError: unknown) => {
      console.error("Failed to send v2 chat message:", sendError);
    });
  };

  return (
    <section
      className="flex h-full min-h-0 flex-col bg-background text-foreground"
      data-testid="chat-surface"
    >
      <Conversation className="min-h-0">
        <ConversationContent className="space-y-4">
          {messages.length === 0 && (
            <div className="mx-auto flex min-h-[40vh] max-w-xl items-center justify-center px-4 text-center text-muted-foreground text-sm">
              Ask a question to start a v2 conversation.
            </div>
          )}
          {messages.map((message) => (
            <MessageParts
              key={message.id}
              isLastMessage={message.id === messages.at(-1)?.id}
              message={message}
              status={status}
            />
          ))}
          {isBusy && <BusyIndicator activity={busyTag} />}
          {error && (
            <div
              className="mx-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-destructive text-sm"
              role="alert"
            >
              {error.message}
            </div>
          )}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      <div className="shrink-0 border-t border-border bg-background/95 p-3">
        <PromptInput onSubmit={handleSubmit}>
          <PromptInputTextarea
            aria-label="Message"
            disabled={status === "submitted"}
            onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setInput(event.target.value)}
            placeholder="Ask Bigweld DA v2"
            value={input}
          />
          <PromptInputToolbar>
            <PromptInputTools>
              {isBusy && (
                <span className="px-2 text-muted-foreground text-xs">
                  {busyTag}
                </span>
              )}
            </PromptInputTools>
            <PromptInputSubmit
              aria-label={status === "streaming" ? "Stop response" : "Send message"}
              disabled={!input.trim() && status !== "streaming"}
              status={status}
            />
          </PromptInputToolbar>
        </PromptInput>
      </div>
    </section>
  );
}

interface MessagePartsProps {
  message: UIMessage;
  status: string;
  isLastMessage: boolean;
}

function MessageParts({ message, status, isLastMessage }: MessagePartsProps) {
  return (
    <article className="space-y-3" data-testid={`message-${message.role}`}>
      {message.parts.map((part, index) => (
        <MessagePart
          key={`${message.id}-${index}`}
          isLastPart={index === message.parts.length - 1}
          isLastMessage={isLastMessage}
          message={message}
          part={part}
          status={status}
        />
      ))}
    </article>
  );
}

interface MessagePartProps {
  message: UIMessage;
  part: UIMessagePart<UIDataTypes, UITools>;
  status: string;
  isLastMessage: boolean;
  isLastPart: boolean;
}

function MessagePart({
  message,
  part,
  status,
  isLastMessage,
  isLastPart,
}: MessagePartProps) {
  if (part.type === "text") {
    return <TextMessage from={message.role} text={part.text} />;
  }

  if (part.type === "reasoning") {
    return (
      <Reasoning
        isStreaming={status === "streaming" && isLastMessage && isLastPart}
        part={part}
      />
    );
  }

  if (isToolUIPart(part)) {
    return (
      <div className="mx-4">
        <ToolCall part={part} />
      </div>
    );
  }

  return null;
}

function latestActivityTag(messages: UIMessage[]): string | null {
  const lastMessage = messages.at(-1);
  if (!lastMessage || lastMessage.role !== "assistant") return null;

  for (const part of [...lastMessage.parts].reverse()) {
    if (part.type === "reasoning") return "thinking";
    if (isToolUIPart(part)) {
      const input = "input" in part ? part.input : undefined;
      return activityTagFromEvent({
        type: "tool",
        toolName: getToolName(part),
        input,
      });
    }
  }

  return null;
}
