import { useFenceDetector } from "@/hooks/useFenceDetector";
import { RenderPanel } from "./RenderPanel";

export function WorkingSpace() {
  useFenceDetector();
  return (
    <div className="h-full bg-background">
      <RenderPanel />
    </div>
  );
}
