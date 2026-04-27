import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/components/layout/ThemeProvider";

export function AppHeader() {
  const { theme, setTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <header className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-background/95 px-4 font-sans backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <img src="/logos/hpe/full-clr-rev.svg" alt="HPE" className="h-6" />
        <span className="text-lg font-semibold tracking-wide text-foreground">Bigweld</span>
      </div>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
        className="text-muted-foreground hover:text-foreground"
        onClick={() => setTheme(isDark ? "light" : "dark")}
      >
        {isDark ? <Sun /> : <Moon />}
      </Button>
    </header>
  );
}
