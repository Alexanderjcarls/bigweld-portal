import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import type { ReactNode } from "react";

interface ResizableShellProps {
  chat: ReactNode;
  workspace: ReactNode;
  download: ReactNode;
}

export function ResizableShell({ chat, workspace, download }: ResizableShellProps) {
  return (
    <ResizablePanelGroup
      direction="horizontal"
      autoSaveId="bigweld-h-split"
      className="h-screen w-screen"
    >
      <ResizablePanel defaultSize={50} minSize={25} maxSize={75}>
        <div className="h-full">{chat}</div>
      </ResizablePanel>
      <ResizableHandle withHandle />
      <ResizablePanel defaultSize={50} minSize={25} maxSize={75}>
        <ResizablePanelGroup direction="vertical">
          <ResizablePanel defaultSize={75} minSize={75} maxSize={75}>
            <div className="h-full">{workspace}</div>
          </ResizablePanel>
          <ResizableHandle disabled />
          <ResizablePanel defaultSize={25} minSize={25} maxSize={25}>
            <div className="h-full">{download}</div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}
