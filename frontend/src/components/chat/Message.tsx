import { motion } from "motion/react";
import { Streamdown } from "streamdown";
import { useChatStore } from "@/stores/chatStore";
import { cn } from "@/lib/utils";

export function Message({ id }: { id: string }) {
  const message = useChatStore(s => s.messages.find(m => m.id === id));
  if (!message) return null;

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
        {message.role === "assistant" ? (
          <Streamdown>{message.content}</Streamdown>
        ) : (
          <div className="whitespace-pre-wrap">{message.content}</div>
        )}
        {message.toolCalls.map((tc, i) => (
          <div key={i} className="mt-2 text-xs opacity-70 border-l-2 pl-2">
            <span className="font-mono">{tc.tool}</span>
            <pre className="mt-1 whitespace-pre-wrap">{tc.output.slice(0, 500)}</pre>
          </div>
        ))}
        {message.isStreaming && <span className="ml-1 inline-block w-2 h-4 bg-current animate-pulse" />}
      </motion.div>
    </div>
  );
}
