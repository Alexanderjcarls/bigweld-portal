import {
  getToolName,
  isToolUIPart,
  type UIDataTypes,
  type UIMessage,
  type UIMessagePart,
  type UITools,
} from "ai";
import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
} from "react";
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
import { useCreateDroppedArtifact, useOpenArtifactReference } from "@/v2/hooks/useArtifacts";
import { useChatStore } from "@/v2/stores/chatStore";
import { useArtifactsStore } from "@/v2/stores/artifactsStore";
import { TextMessage } from "@/v2/components/chat/Message";
import { Reasoning } from "@/v2/components/chat/Reasoning";
import { ToolCall } from "@/v2/components/chat/ToolCall";
import {
  activityTagFromEvent,
  activityTagFromToolCall,
  BusyIndicator,
} from "@/v2/components/chat/BusyIndicator";
import { dispatchContextStatsChatEvent } from "@/v2/hooks/useContextStats";
import { extractArtifactReferences } from "@/v2/lib/artifact-references";

export function ChatSurface() {
  const [input, setInput] = useState("");
  const [activityTag, setActivityTag] = useState("working");
  const conversationId = useChatStore((state) => state.conversationId);
  const setLastSubmittedText = useChatStore((state) => state.setLastSubmittedText);
  const setMessageCount = useChatStore((state) => state.setMessageCount);
  const hydratedConversationId = useChatStore((state) => state.hydratedConversationId);
  const hydratedMessages = useChatStore((state) => state.hydratedMessages);
  const clearHydratedConversation = useChatStore((state) => state.clearHydratedConversation);
  const closeSidecar = useArtifactsStore((state) => state.closeSidecar);
  const revealDropZone = useArtifactsStore((state) => state.revealDropZone);
  const openArtifactReference = useOpenArtifactReference();
  const droppedArtifact = useCreateDroppedArtifact(conversationId);
  const lastAutoOpenedReference = useRef<string | null>(null);
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

  useEffect(() => {
    const reference = latestArtifactReference(messages);
    if (!reference || reference === lastAutoOpenedReference.current) return;

    lastAutoOpenedReference.current = reference;
    openArtifactReference(reference).catch((openError: unknown) => {
      console.error("Failed to auto-open artifact reference:", openError);
    });
  }, [messages, openArtifactReference]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (status === "streaming") {
      stop();
      return;
    }

    const text = input.trim();
    if (!text || status === "submitted") return;

    if (isArtifactCloseCommand(text)) {
      closeSidecar();
      setInput("");
      return;
    }

    setLastSubmittedText(text);
    setInput("");
    sendMessage({ text }).catch((sendError: unknown) => {
      console.error("Failed to send v2 chat message:", sendError);
    });
  };

  const handleDragEnter = (event: DragEvent<HTMLElement>) => {
    if (!eventHasFiles(event)) return;
    event.preventDefault();
    revealDropZone();
  };

  const handleDragOver = (event: DragEvent<HTMLElement>) => {
    if (!eventHasFiles(event)) return;
    event.preventDefault();
  };

  const handleDrop = (event: DragEvent<HTMLElement>) => {
    if (!eventHasFiles(event)) return;
    event.preventDefault();
    const [file] = Array.from(event.dataTransfer.files);
    if (file) droppedArtifact.mutate(file);
  };

  return (
    <section
      className="flex h-full min-h-0 flex-col bg-background text-foreground"
      data-testid="chat-surface"
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
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

function latestArtifactReference(messages: UIMessage[]): string | null {
  for (const message of [...messages].reverse()) {
    for (const part of [...message.parts].reverse()) {
      const reference = artifactReferenceFromPart(part);
      if (reference) return reference;
    }
  }

  return null;
}

function artifactReferenceFromPart(
  part: UIMessagePart<UIDataTypes, UITools>,
): string | null {
  if (part.type === "text") {
    return extractArtifactReferences(part.text).at(-1) ?? null;
  }

  if (isToolUIPart(part) && part.state === "output-available") {
    return artifactReferenceFromValue(part.output);
  }

  return artifactReferenceFromValue(part);
}

function artifactReferenceFromValue(value: unknown): string | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;

  for (const key of ["artifact_id", "artifactId", "id", "slug"]) {
    const candidate = record[key];
    if (typeof candidate === "string" && isArtifactLikeRecord(record)) {
      return candidate;
    }
  }

  const artifact = record.artifact;
  if (artifact && typeof artifact === "object" && !Array.isArray(artifact)) {
    return artifactReferenceFromValue(artifact);
  }

  return null;
}

function isArtifactLikeRecord(record: Record<string, unknown>): boolean {
  return (
    record.kind === "artifact" ||
    record.type === "artifact" ||
    record.event === "artifact_created" ||
    "artifact_id" in record ||
    "artifactId" in record
  );
}

function isArtifactCloseCommand(text: string): boolean {
  return /^(close|dismiss)(\s+(artifact|sidecar|artifacts))?\.?$/i.test(text.trim());
}

function eventHasFiles(event: DragEvent<HTMLElement>): boolean {
  return Array.from(event.dataTransfer.types).includes("Files");
}
