import { useCallback } from "react";
import { useStreamJsonChat } from "@/hooks/useStreamJsonChat";
import { useResumeStore } from "@/stores/resumeStore";

export function useResumeOnDisconnect() {
  const lastMessage = useResumeStore(s => s.lastFailedMessage);
  const setLastFailedMessage = useResumeStore(s => s.setLastFailedMessage);
  const clear = useResumeStore(s => s.clear);
  const { sendTurn } = useStreamJsonChat();

  const onDisconnect = useCallback((message: string) => {
    setLastFailedMessage(message);
  }, [setLastFailedMessage]);

  const resume = useCallback(async () => {
    if (!lastMessage) return;
    const message = lastMessage;
    clear();
    await sendTurn(message);
  }, [clear, lastMessage, sendTurn]);

  const dismiss = useCallback(() => {
    clear();
  }, [clear]);

  return { show: lastMessage !== null, lastMessage, onDisconnect, resume, dismiss };
}
