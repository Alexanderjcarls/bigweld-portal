import { useChat as useAiChat } from "@ai-sdk/react";
import { DefaultChatTransport, type ChatInit, type UIMessage } from "ai";
import { useMemo } from "react";
import { buildChatRequestBody, getChatApiUrl } from "@/v2/lib/api";
import { useChatStore } from "@/v2/stores/chatStore";

type V2UseChatOptions = Omit<ChatInit<UIMessage>, "id" | "transport"> & {
  experimental_throttle?: number;
  resume?: boolean;
};

export function useChat(options: V2UseChatOptions = {}) {
  const conversationId = useChatStore((state) => state.conversationId);

  const transport = useMemo(
    () =>
      new DefaultChatTransport<UIMessage>({
        api: getChatApiUrl(),
        credentials: "omit",
        prepareSendMessagesRequest: ({
          id,
          messages,
          trigger,
          messageId,
          body,
        }) => ({
          body: buildChatRequestBody({
            chatId: id,
            conversationId,
            messages,
            trigger,
            messageId,
            body,
          }),
          credentials: "omit",
        }),
      }),
    [conversationId],
  );

  return useAiChat<UIMessage>({
    experimental_throttle: 50,
    ...options,
    id: conversationId,
    transport,
  });
}
