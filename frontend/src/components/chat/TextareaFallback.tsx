import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useChatStore } from "@/stores/chatStore";
import { useStreamJsonChat } from "@/hooks/useStreamJsonChat";

export function TextareaFallback() {
  const [text, setText] = useState("");
  const { sendTurn } = useStreamJsonChat();
  const isStreaming = useChatStore(s => s.isStreaming);

  return (
    <div className="border-t p-4 space-y-2 font-sans bg-yellow-50/30">
      <p className="text-xs text-amber-700">Editor degraded — please refresh.</p>
      <textarea
        className="w-full min-h-[80px] border rounded p-2"
        value={text}
        onChange={e => setText(e.target.value)}
      />
      <Button onClick={async () => { await sendTurn(text); setText(""); }} disabled={isStreaming}>Send</Button>
    </div>
  );
}
