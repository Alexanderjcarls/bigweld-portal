import {
  CodeIcon,
  DatabaseIcon,
  DownloadIcon,
  FileSearchIcon,
  GlobeIcon,
  ImagePlusIcon,
  SearchIcon,
  TerminalIcon,
  WrenchIcon,
} from "lucide-react";
import type { ReactNode } from "react";

export function getToolIcon(toolId: string, className = "size-4"): ReactNode {
  const normalized = toolId.toLowerCase().replaceAll("-", "_");
  const iconMap: Record<string, ReactNode> = {
    bash: <TerminalIcon className={className} />,
    code_execution: <CodeIcon className={className} />,
    database: <DatabaseIcon className={className} />,
    file_search: <FileSearchIcon className={className} />,
    image_generation: <ImagePlusIcon className={className} />,
    search: <SearchIcon className={className} />,
    web_fetch: <DownloadIcon className={className} />,
    web_search: <GlobeIcon className={className} />,
  };

  return iconMap[normalized] ?? <WrenchIcon className={className} />;
}
