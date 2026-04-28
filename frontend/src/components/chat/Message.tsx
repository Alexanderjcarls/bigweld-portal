import { motion } from "motion/react";
import { Streamdown } from "streamdown";
import { useShallow } from "zustand/react/shallow";
import { useChatStore } from "@/stores/chatStore";
import { cn } from "@/lib/utils";
import type { MessageBlock } from "@/types/conversation";

export function Message({ id }: { id: string }) {
  const message = useChatStore(useShallow(s => s.messages.find(m => m.id === id)));
  if (!message) return null;
  const lastTextBlockIndex = findLastTextBlockIndex(message.blocks);

  return (
    <div className={cn("flex w-full mb-4", message.role === "user" ? "justify-end" : "justify-start")}>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.18 }}
        className={cn(
          "max-w-prose px-4 py-3 rounded-lg font-sans",
          message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
        )}
      >
        <div className="space-y-3">
          {message.blocks.map((block, index) => (
            <BlockRenderer
              key={`${block.kind}-${index}`}
              block={block}
              role={message.role}
              showCaret={message.isStreaming && index === lastTextBlockIndex}
            />
          ))}
          {message.isStreaming && lastTextBlockIndex === -1 && (
            <span className="inline-block h-4 w-2 animate-pulse bg-current align-middle" />
          )}
        </div>
      </motion.div>
    </div>
  );
}

function BlockRenderer({
  block,
  role,
  showCaret,
}: {
  block: MessageBlock;
  role: "user" | "assistant" | "system";
  showCaret: boolean;
}) {
  if (block.kind === "tool_use") {
    return <ToolUseBlock block={block} />;
  }
  if (block.kind === "thinking") {
    return <ThinkingBlock text={block.text} />;
  }
  if (role === "assistant") {
    return (
      <div className="min-w-0">
        <Streamdown>{block.text}</Streamdown>
        {showCaret && <span className="ml-1 inline-block h-4 w-2 animate-pulse bg-current align-middle" />}
      </div>
    );
  }
  return (
    <div className="whitespace-pre-wrap break-words">
      {block.text}
      {showCaret && <span className="ml-1 inline-block h-4 w-2 animate-pulse bg-current align-middle" />}
    </div>
  );
}

function ToolUseBlock({ block }: { block: Extract<MessageBlock, { kind: "tool_use" }> }) {
  const fullInput = fullInputText(block);
  return (
    <details className="group rounded border border-primary/40 bg-background/45 p-3 text-xs text-muted-foreground">
      <summary className="flex cursor-pointer list-none items-center gap-2 [&::-webkit-details-marker]:hidden">
        {block.isStreaming && <span className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-primary" />}
        <span className="shrink-0 font-mono text-foreground">{block.name}</span>
        <span className="min-w-0 truncate font-mono">{toolPreview(block)}</span>
      </summary>
      <div className="mt-3 space-y-3 font-mono">
        <pre className="max-h-64 overflow-auto rounded bg-muted/70 p-2 whitespace-pre-wrap break-words text-foreground">{fullInput}</pre>
        <output className="block">
          <pre className="max-h-96 overflow-auto rounded bg-muted/70 p-2 whitespace-pre-wrap break-words text-foreground">{block.output ?? ""}</pre>
        </output>
        {block.error && (
          <pre className="overflow-auto rounded border border-destructive/40 bg-destructive/10 p-2 whitespace-pre-wrap break-words text-destructive">{block.error}</pre>
        )}
      </div>
    </details>
  );
}

function ThinkingBlock({ text }: { text: string }) {
  const body = (
    <div className="border-l border-border pl-3 italic text-muted-foreground whitespace-pre-wrap break-words">
      {text}
    </div>
  );
  if (text.length <= 200) return body;
  return (
    <details className="text-sm text-muted-foreground">
      <summary className="cursor-pointer italic">Thinking</summary>
      <div className="mt-2">{body}</div>
    </details>
  );
}

function findLastTextBlockIndex(blocks: MessageBlock[]): number {
  for (let i = blocks.length - 1; i >= 0; i -= 1) {
    if (blocks[i].kind === "text") return i;
  }
  return -1;
}

function toolPreview(block: Extract<MessageBlock, { kind: "tool_use" }>): string {
  if (block.name === "Bash" && typeof block.input.command === "string") {
    return truncate(block.input.command, 80);
  }
  return truncate(stringifyInput(block.input), 80);
}

function fullInputText(block: Extract<MessageBlock, { kind: "tool_use" }>): string {
  if (block.name === "Bash" && typeof block.input.command === "string") {
    return block.input.command;
  }
  return JSON.stringify(block.input, null, 2);
}

function stringifyInput(input: Record<string, unknown>): string {
  try {
    return JSON.stringify(input);
  } catch {
    return String(input);
  }
}

function truncate(value: string, max: number): string {
  return value.length > max ? `${value.slice(0, max - 1)}...` : value;
}
