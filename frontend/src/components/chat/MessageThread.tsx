import { useChatStore } from "@/stores/chatStore";
import { Message } from "./Message";
import { useEffect, useRef } from "react";

export function MessageThread() {
  const messageIds = useChatStore(s => s.messages.map(m => m.id));
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messageIds.length]);

  return (
    <div className="flex-1 overflow-y-auto p-4">
      {messageIds.map(id => <Message key={id} id={id} />)}
      <div ref={bottomRef} />
    </div>
  );
}
