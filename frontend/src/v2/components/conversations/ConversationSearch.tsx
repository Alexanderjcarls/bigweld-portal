import { SearchIcon } from "lucide-react";
import { Input } from "@/components/ui/input";

interface ConversationSearchProps {
  value: string;
  onChange: (value: string) => void;
}

export function ConversationSearch({ value, onChange }: ConversationSearchProps) {
  return (
    <label className="relative block">
      <span className="sr-only">Filter conversations</span>
      <SearchIcon className="-translate-y-1/2 pointer-events-none absolute top-1/2 left-2.5 size-4 text-muted-foreground" />
      <Input
        aria-label="Filter conversations"
        className="h-8 pl-8 text-sm"
        onChange={(event) => onChange(event.target.value)}
        placeholder="Filter conversations"
        type="search"
        value={value}
      />
    </label>
  );
}
