import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/components/layout/ThemeProvider";
import { ResizableShell } from "@/components/layout/ResizableShell";
import { ChatSurface } from "@/components/chat/ChatSurface";

const queryClient = new QueryClient();

function WorkspacePlaceholder() {
  return (
    <div className="h-full flex items-center justify-center bg-muted/30">
      <p className="text-muted-foreground font-sans">Working space (Phase 10)</p>
    </div>
  );
}

function DownloadPlaceholder() {
  return (
    <div className="h-full flex items-center justify-center bg-muted/10 border-t">
      <p className="text-muted-foreground font-sans text-sm">Download zone (Phase 10)</p>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ResizableShell
          chat={<ChatSurface />}
          workspace={<WorkspacePlaceholder />}
          download={<DownloadPlaceholder />}
        />
      </ThemeProvider>
    </QueryClientProvider>
  );
}
