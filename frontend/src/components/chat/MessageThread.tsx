import { useChatStore } from "@/stores/chatStore";
import { Message } from "./Message";
import { useEffect, useRef } from "react";
import { useShallow } from "zustand/react/shallow";

export function MessageThread() {
  const messageIds = useChatStore(useShallow(s => s.messages.map(m => m.id)));
  const lastMessageSize = useChatStore(s => {
    const last = s.messages[s.messages.length - 1];
    if (!last) return 0;
    let n = last.blocks.length;
    for (const b of last.blocks) {
      if (b.kind === "text" || b.kind === "thinking") n += b.text.length;
      else if (b.kind === "tool_use") n += (b.output?.length ?? 0);
    }
    return n;
  });
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messageIds.length, lastMessageSize]);

  if (messageIds.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
        <img src="/logos/hpe/full-clr-rev.svg" alt="HPE" className="h-12 opacity-90" />
        <h1 className="font-sans text-3xl font-semibold tracking-tight">Bigweld</h1>
        <p className="text-base italic text-muted-foreground">"See a need, fill a need!"</p>
        <p className="mt-4 max-w-md text-center text-sm text-muted-foreground">
          Your work-augmentation DA. Ask about scope, gaps, articles, customers, or anything in the Bigweld knowledge graph.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4">
      {messageIds.map(id => <Message key={id} id={id} />)}
      <div ref={bottomRef} />
    </div>
  );
}
