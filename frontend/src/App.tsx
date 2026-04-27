import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/components/layout/ThemeProvider";
import { ResizableShell } from "@/components/layout/ResizableShell";

const queryClient = new QueryClient();

function ChatPlaceholder() {
  return (
    <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
      <img src="/logos/hpe/full-clr-pos.svg" alt="HPE" className="h-8 mb-4 dark:hidden" />
      <img src="/logos/hpe/full-clr-rev.svg" alt="HPE" className="h-8 mb-4 hidden dark:block" />
      <p className="font-sans">Bigweld — chat surface (Phase 9)</p>
    </div>
  );
}

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
          chat={<ChatPlaceholder />}
          workspace={<WorkspacePlaceholder />}
          download={<DownloadPlaceholder />}
        />
      </ThemeProvider>
    </QueryClientProvider>
  );
}
