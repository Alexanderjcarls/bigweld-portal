import type { ReasoningUIPart } from "ai";
import {
  Reasoning as AIReasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/v2/components/ai-elements/reasoning";

interface ReasoningProps {
  part: ReasoningUIPart;
  isStreaming?: boolean;
}

export function Reasoning({ part, isStreaming = false }: ReasoningProps) {
  if (!part.text.trim()) return null;

  return (
    <AIReasoning
      className="mx-4"
      defaultOpen={false}
      isStreaming={isStreaming}
    >
      <ReasoningTrigger />
      <ReasoningContent>{part.text}</ReasoningContent>
    </AIReasoning>
  );
}
