import { FolderOpenIcon, MoonIcon, SunIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/components/layout/ThemeProvider";
import { CompactButton } from "@/v2/components/header/CompactButton";
import { ContextBar } from "@/v2/components/header/ContextBar";
import { useArtifactsStore } from "@/v2/stores/artifactsStore";

export function AppHeader() {
  const { theme, setTheme } = useTheme();
  const openPicker = useArtifactsStore((state) => state.openPicker);
  const isDark = theme === "dark";

  return (
    <header
      className="flex h-12 shrink-0 items-center gap-3 border-b border-border bg-background/95 px-4 font-sans backdrop-blur-sm"
      data-testid="v2-app-header"
    >
      <div className="flex min-w-0 items-center gap-3">
        <img
          alt="HPE"
          className="h-6 w-auto shrink-0"
          src="/logos/hpe/full-clr-rev.svg"
        />
        <span className="truncate text-lg font-semibold text-foreground">Bigweld</span>
      </div>
      <div className="min-w-0 flex-1" />
      <ContextBar />
      <Button
        aria-label="Browse artifacts"
        className="text-muted-foreground hover:text-foreground"
        onClick={openPicker}
        size="icon-sm"
        type="button"
        variant="ghost"
      >
        <FolderOpenIcon className="size-4" />
      </Button>
      <CompactButton />
      <Button
        aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
        className="text-muted-foreground hover:text-foreground"
        onClick={() => setTheme(isDark ? "light" : "dark")}
        size="icon-sm"
        type="button"
        variant="ghost"
      >
        {isDark ? <SunIcon className="size-4" /> : <MoonIcon className="size-4" />}
      </Button>
    </header>
  );
}
