import { MessageThread } from "./MessageThread";
import { ChatInput } from "./ChatInput";
import { ContextBars } from "./ContextBars";
import { SessionControls } from "./SessionControls";

export function ChatSurface() {
  return (
    <div className="flex flex-col h-full">
      <MessageThread />
      <div className="border-t">
        <ChatInput />
        <div className="flex justify-between items-center px-4 pb-3">
          <ContextBars />
          <SessionControls />
        </div>
      </div>
    </div>
  );
}
