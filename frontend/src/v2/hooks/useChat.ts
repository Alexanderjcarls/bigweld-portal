import { useChat as useAiChat, type UseChatOptions } from "@ai-sdk/react";
import { DefaultChatTransport, type UIMessage } from "ai";
import { useMemo } from "react";
import { buildChatRequestBody, getChatApiUrl } from "@/v2/lib/api";
import { useChatStore } from "@/v2/stores/chatStore";

export function useChat(options: Omit<UseChatOptions<UIMessage>, "id" | "transport"> = {}) {
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
