import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import { useChatStore } from "@/stores/chatStore";

const SKILLS = [
  { name: "graph", desc: "substrate manual" },
  { name: "gaps", desc: "sparse-coverage analyzer" },
  { name: "orphans", desc: "no-inbound articles" },
  { name: "rollup", desc: "scope coverage summary" },
  { name: "dupes", desc: "near-duplicate finder" },
  { name: "citations", desc: "most-traversed by topic" },
  { name: "search-past-conversations", desc: "grep prior summaries" },
];

export function SessionControls() {
  const reset = useChatStore(s => s.reset);
  const setInputDraft = useChatStore(s => s.setInputDraft);

  return (
    <div className="flex gap-2 items-center font-sans">
      <Button size="sm" variant="outline" onClick={() => reset()}>+ New</Button>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button size="sm" variant="outline">Skills ▾</Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          {SKILLS.map(s => (
            <DropdownMenuItem
              key={s.name}
              onClick={() => setInputDraft(`/${s.name} `)}
            >
              <span className="font-mono mr-2">/{s.name}</span>
              <span className="text-xs text-muted-foreground">{s.desc}</span>
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
