import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/components/layout/ThemeProvider";
import { ChatSurface } from "@/v2/components/chat/ChatSurface";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <main className="h-screen w-screen overflow-hidden bg-background text-foreground">
          <ChatSurface />
        </main>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
