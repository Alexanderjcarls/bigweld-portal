import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import {
  Message as AIMessage,
  MessageContent,
} from "@/v2/components/ai-elements/message";
import { Response } from "@/v2/components/ai-elements/response";
import { useOpenArtifactReference } from "@/v2/hooks/useArtifacts";
import { splitArtifactReferences } from "@/v2/lib/artifact-references";

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
      <ArtifactAwareText text={text} />
    </ChatMessage>
  );
}

function ArtifactAwareText({ text }: { text: string }) {
  const openArtifactReference = useOpenArtifactReference();
  const segments = splitArtifactReferences(text);

  if (segments.length === 1 && segments[0]?.type === "text") {
    return <Response>{text}</Response>;
  }

  return (
    <div className="whitespace-pre-wrap text-sm leading-6">
      {segments.map((segment, index) => {
        if (segment.type === "text") {
          return <span key={`${index}-text`}>{segment.value}</span>;
        }

        return (
          <Button
            className="inline h-auto min-h-0 px-1 py-0 align-baseline font-mono text-xs"
            key={`${index}-${segment.value}`}
            onClick={() => {
              openArtifactReference(segment.value).catch((error: unknown) => {
                console.error("Failed to open artifact reference:", error);
              });
            }}
            type="button"
            variant="link"
          >
            @artifact:{segment.value}
          </Button>
        );
      })}
    </div>
  );
}
