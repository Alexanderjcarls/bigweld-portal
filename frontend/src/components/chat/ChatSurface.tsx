import { MessageThread } from "./MessageThread";
import { ChatInput } from "./ChatInput";
import { ChatInputBoundary } from "./ChatInputBoundary";
import { ContextBars } from "./ContextBars";
import { ResumeBanner } from "./ResumeBanner";
import { SessionControls } from "./SessionControls";
import { TextareaFallback } from "./TextareaFallback";

export function ChatSurface() {
  return (
    <div className="flex flex-col h-full">
      <MessageThread />
      <div className="border-t">
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
