import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/components/layout/ThemeProvider";
import { ResizableShell } from "@/components/layout/ResizableShell";
import { ChatSurface } from "@/components/chat/ChatSurface";
import { WorkingSpace } from "@/components/workspace/WorkingSpace";
import { DownloadZone } from "@/components/workspace/DownloadZone";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ResizableShell
          chat={<ChatSurface />}
          workspace={<WorkingSpace />}
          download={<DownloadZone />}
        />
      </ThemeProvider>
    </QueryClientProvider>
  );
}
