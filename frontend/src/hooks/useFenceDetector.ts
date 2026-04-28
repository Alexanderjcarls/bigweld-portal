import { useEffect } from "react";
import { useChatStore } from "@/stores/chatStore";
import { useWorkspaceStore } from "@/stores/workspaceStore";

const FENCE_RE = /```(mermaid|d2|plantuml|graphviz|structurizr|bpmn)\n([\s\S]+?)```/g;

/** Watches the latest assistant message; if it contains a fenced diagram block,
 * tees the SOURCE (last block wins, per replace pattern) into workspaceStore. */
export function useFenceDetector(): void {
  const lastAssistantContent = useChatStore(
    s => s.messages
      .filter(m => m.role === "assistant")
      .slice(-1)[0]
      ?.blocks
      .filter(block => block.kind === "text")
      .map(block => block.text)
      .join("\n")
  );
  const setSource = useWorkspaceStore(s => s.setSource);

  useEffect(() => {
    if (!lastAssistantContent) return;
    const matches = Array.from(lastAssistantContent.matchAll(FENCE_RE));
    const lastMatch = matches.at(-1);
    if (!lastMatch) return;
    const [, kind, source] = lastMatch;
    if (kind === "mermaid") setSource("mermaid", source.trim());
    else if (kind === "d2") setSource("d2", source.trim());
    else setSource("kroki", source.trim(), kind);
  }, [lastAssistantContent, setSource]);
}
