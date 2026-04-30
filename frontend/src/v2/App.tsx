import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/components/layout/ThemeProvider";
import { ChatSurface } from "@/v2/components/chat/ChatSurface";
import { ConversationSidebar } from "@/v2/components/conversations/ConversationSidebar";
import { AppHeader } from "@/v2/components/header/AppHeader";
import { ArtifactSidecar } from "@/v2/components/sidecar/ArtifactSidecar";
import { useChatStore } from "@/v2/stores/chatStore";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <V2Shell />
      </ThemeProvider>
    </QueryClientProvider>
  );
}

function V2Shell() {
  const conversationId = useChatStore((state) => state.conversationId);

  return (
    <main className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      <ConversationSidebar />
      <section className="flex min-w-0 flex-1 flex-col">
        <AppHeader />
        <ChatSurface />
      </section>
      <ArtifactSidecar conversationId={conversationId} />
    </main>
  );
}
