import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/components/layout/ThemeProvider";
import { AppHeader } from "@/components/layout/AppHeader";
import { ResizableShell } from "@/components/layout/ResizableShell";
import { ChatSurface } from "@/components/chat/ChatSurface";
import { WorkingSpace } from "@/components/workspace/WorkingSpace";
import { DownloadZone } from "@/components/workspace/DownloadZone";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <div className="flex h-screen w-screen flex-col bg-background text-foreground">
          <AppHeader />
          <div className="min-h-0 flex-1">
            <ResizableShell
              chat={<ChatSurface />}
              workspace={<WorkingSpace />}
              download={<DownloadZone />}
            />
          </div>
        </div>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
