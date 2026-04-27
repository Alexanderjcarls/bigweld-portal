import { Button } from "@/components/ui/button";
import { useResumeOnDisconnect } from "@/hooks/useResumeOnDisconnect";

export function ResumeBanner() {
  const { show, resume, dismiss } = useResumeOnDisconnect();
  if (!show) return null;
  return (
    <div className="border-t border-amber-300 bg-amber-50 px-4 py-2 flex items-center justify-between font-sans text-sm">
      <span className="text-amber-900">Connection lost mid-stream.</span>
      <div className="flex gap-2">
        <Button size="sm" variant="outline" onClick={dismiss}>Dismiss</Button>
        <Button size="sm" onClick={resume}>Resume</Button>
      </div>
    </div>
  );
}
