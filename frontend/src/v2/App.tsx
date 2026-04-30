import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/components/layout/ThemeProvider";
import { ChatSurface } from "@/v2/components/chat/ChatSurface";
import { ConversationSidebar } from "@/v2/components/conversations/ConversationSidebar";
import { AppHeader } from "@/v2/components/header/AppHeader";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <main className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
          <ConversationSidebar />
          <section className="flex min-w-0 flex-1 flex-col">
            <AppHeader />
            <ChatSurface />
          </section>
        </main>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
