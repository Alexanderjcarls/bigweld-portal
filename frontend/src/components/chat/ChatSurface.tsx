import { MessageThread } from "./MessageThread";
import { ChatInput } from "./ChatInput";
import { ChatInputBoundary } from "./ChatInputBoundary";
import { ContextBars } from "./ContextBars";
import { ResumeBanner } from "./ResumeBanner";
import { SessionControls } from "./SessionControls";
import { TextareaFallback } from "./TextareaFallback";

export function ChatSurface() {
  return (
    <div className="flex h-full flex-col border-r border-border bg-card">
      <MessageThread />
      <div className="border-t border-border bg-card/50">
        <ResumeBanner />
        <ChatInputBoundary fallback={<TextareaFallback />}>
          <ChatInput />
        </ChatInputBoundary>
        <div className="flex justify-between items-center px-4 pb-3">
          <ContextBars />
          <SessionControls />
        </div>
      </div>
    </div>
  );
}
